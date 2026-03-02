"""
余额管理模块自动化测试：
1. 账户 CRUD（创建、查询、更新、删除）
2. 月度余额 upsert、查询、删除
3. CSV 导出格式验证
4. CSV 导入（正常 + 边界值 + 错误数据）
5. 导入-导出往返一致性（round-trip）
6. 趋势接口
"""
import csv
import io

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def make_csv(rows: list[dict], fieldnames: list[str]) -> bytes:
    """把 rows 列表序列化为 CSV bytes（UTF-8 with BOM）。"""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 账户 CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestAccountCRUD:

    def test_list_accounts_auto_init(self, client, auth_headers):
        """首次获取账户列表时自动初始化 6 个默认账户。"""
        resp = client.get("/api/income/accounts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 6
        names = [a["name"] for a in data]
        assert "微众银行" in names
        assert "腾讯股票" in names

    def test_create_account(self, client, auth_headers):
        resp = client.post(
            "/api/income/accounts",
            json={"name": "支付宝", "sort_order": 10},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "支付宝"
        assert body["is_active"] is True

    def test_create_duplicate_account_fails(self, client, auth_headers):
        """创建同名账户应返回 409。"""
        client.get("/api/income/accounts", headers=auth_headers)  # 触发默认账户初始化
        resp = client.post(
            "/api/income/accounts",
            json={"name": "微众银行"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_update_account_name(self, client, auth_headers):
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        first_id = accs[0]["id"]
        resp = client.put(
            f"/api/income/accounts/{first_id}",
            json={"name": "招行储蓄"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "招行储蓄"

    def test_update_account_sort_order(self, client, auth_headers):
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        first_id = accs[0]["id"]
        resp = client.put(
            f"/api/income/accounts/{first_id}",
            json={"sort_order": 99},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["sort_order"] == 99

    def test_delete_account_soft(self, client, auth_headers):
        """删除账户（软删除）后，账户列表中不再出现。"""
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        target_id = accs[-1]["id"]
        resp = client.delete(f"/api/income/accounts/{target_id}", headers=auth_headers)
        assert resp.status_code == 204

        remaining = client.get("/api/income/accounts", headers=auth_headers).json()
        ids = [a["id"] for a in remaining]
        assert target_id not in ids

    def test_delete_nonexistent_account(self, client, auth_headers):
        resp = client.delete("/api/income/accounts/99999", headers=auth_headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 月度余额 upsert / 查询 / 删除
# ═══════════════════════════════════════════════════════════════════════════════

class TestMonthlyBalances:

    def _get_account_ids(self, client, auth_headers):
        return [a["id"] for a in client.get("/api/income/accounts", headers=auth_headers).json()]

    def test_upsert_and_get_month(self, client, auth_headers):
        ids = self._get_account_ids(client, auth_headers)
        balances = [{"account_id": ids[0], "balance": 10000.0},
                    {"account_id": ids[1], "balance": 20000.5}]
        resp = client.post(
            "/api/income/balances",
            json={"month": "2026-01", "balances": balances},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["month"] == "2026-01"
        assert abs(data["total"] - 30000.5) < 0.01

    def test_upsert_overwrites_existing(self, client, auth_headers):
        ids = self._get_account_ids(client, auth_headers)
        # 第一次写入
        client.post(
            "/api/income/balances",
            json={"month": "2026-02", "balances": [{"account_id": ids[0], "balance": 5000.0}]},
            headers=auth_headers,
        )
        # 第二次写入同月同账户
        client.post(
            "/api/income/balances",
            json={"month": "2026-02", "balances": [{"account_id": ids[0], "balance": 9999.99}]},
            headers=auth_headers,
        )
        detail = client.get("/api/income/balances/2026-02", headers=auth_headers).json()
        item = next(i for i in detail["items"] if i["account_id"] == ids[0])
        assert abs(item["balance"] - 9999.99) < 0.001

    def test_list_months(self, client, auth_headers):
        ids = self._get_account_ids(client, auth_headers)
        for month in ["2025-10", "2025-11", "2025-12"]:
            client.post(
                "/api/income/balances",
                json={"month": month, "balances": [{"account_id": ids[0], "balance": 1000.0}]},
                headers=auth_headers,
            )
        resp = client.get("/api/income/balances", headers=auth_headers)
        assert resp.status_code == 200
        months = [s["month"] for s in resp.json()]
        assert "2025-12" in months
        assert "2025-10" in months
        # 默认倒序
        assert months.index("2025-12") < months.index("2025-10")

    def test_delete_month(self, client, auth_headers):
        ids = self._get_account_ids(client, auth_headers)
        client.post(
            "/api/income/balances",
            json={"month": "2026-03", "balances": [{"account_id": ids[0], "balance": 100.0}]},
            headers=auth_headers,
        )
        resp = client.delete("/api/income/balances/2026-03", headers=auth_headers)
        assert resp.status_code == 204

        resp2 = client.get("/api/income/balances/2026-03", headers=auth_headers)
        assert resp2.status_code == 404

    def test_invalid_month_format(self, client, auth_headers):
        ids = self._get_account_ids(client, auth_headers)
        resp = client.post(
            "/api/income/balances",
            json={"month": "2026-13", "balances": [{"account_id": ids[0], "balance": 0}]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_invalid_account_id(self, client, auth_headers):
        resp = client.post(
            "/api/income/balances",
            json={"month": "2026-01", "balances": [{"account_id": 99999, "balance": 100}]},
            headers=auth_headers,
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CSV 导出格式验证
# ═══════════════════════════════════════════════════════════════════════════════

class TestCsvExport:

    def test_export_empty(self, client, auth_headers):
        """无数据时导出空 CSV（仅含表头）。"""
        client.get("/api/income/accounts", headers=auth_headers)  # 触发初始化
        resp = client.get("/api/income/export/csv", headers=auth_headers)
        assert resp.status_code == 200
        text = resp.content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        assert len(rows) == 1  # 仅表头
        assert rows[0][0] == "月份"
        assert "总资产" in rows[0]

    def test_export_with_data(self, client, auth_headers):
        ids = [a["id"] for a in client.get("/api/income/accounts", headers=auth_headers).json()]
        # 写入两个月的数据
        for month, balance in [("2025-11", 10000.0), ("2025-12", 20000.0)]:
            client.post(
                "/api/income/balances",
                json={"month": month, "balances": [{"account_id": ids[0], "balance": balance}]},
                headers=auth_headers,
            )
        resp = client.get("/api/income/export/csv", headers=auth_headers)
        text = resp.content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        assert len(rows) == 3  # 表头 + 2 行数据
        month_col = [r[0] for r in rows[1:]]
        assert "2025-11" in month_col
        assert "2025-12" in month_col

    def test_export_total_column_correct(self, client, auth_headers):
        """导出数据中「总资产」列应等于各账户之和。"""
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        ids = [a["id"] for a in accs]
        balances = [{"account_id": ids[0], "balance": 1000.0},
                    {"account_id": ids[1], "balance": 2000.0},
                    {"account_id": ids[2], "balance": 3000.0}]
        client.post(
            "/api/income/balances",
            json={"month": "2026-01", "balances": balances},
            headers=auth_headers,
        )
        resp = client.get("/api/income/export/csv", headers=auth_headers)
        text = resp.content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        row = next(reader)
        assert abs(float(row["总资产"]) - 6000.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CSV 导入
# ═══════════════════════════════════════════════════════════════════════════════

class TestCsvImport:

    def test_import_creates_balances(self, client, auth_headers):
        """正常 CSV 导入后数据可被正确查询。"""
        client.get("/api/income/accounts", headers=auth_headers)  # 初始化默认账户
        csv_bytes = make_csv(
            [{"月份": "2026-01", "微众银行": "5000", "招商银行": "3000"}],
            fieldnames=["月份", "微众银行", "招商银行"],
        )
        resp = client.post(
            "/api/income/import/csv",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["inserted"] == 2
        assert result["updated"] == 0

        snapshot = client.get("/api/income/balances/2026-01", headers=auth_headers).json()
        items_by_name = {i["account_name"]: i["balance"] for i in snapshot["items"]}
        assert abs(items_by_name["微众银行"] - 5000.0) < 0.01
        assert abs(items_by_name["招商银行"] - 3000.0) < 0.01

    def test_import_updates_existing(self, client, auth_headers):
        """对已存在的月份再次导入时，余额应被更新。"""
        client.get("/api/income/accounts", headers=auth_headers)
        for val in ["1000", "9999"]:
            csv_bytes = make_csv(
                [{"月份": "2026-02", "微众银行": val}],
                fieldnames=["月份", "微众银行"],
            )
            client.post(
                "/api/income/import/csv",
                files={"file": ("t.csv", csv_bytes, "text/csv")},
                headers=auth_headers,
            )
        snapshot = client.get("/api/income/balances/2026-02", headers=auth_headers).json()
        item = next(i for i in snapshot["items"] if i["account_name"] == "微众银行")
        assert abs(item["balance"] - 9999.0) < 0.01

    def test_import_auto_creates_new_account(self, client, auth_headers):
        """导入包含新账户名称的 CSV，应自动创建该账户。"""
        client.get("/api/income/accounts", headers=auth_headers)
        csv_bytes = make_csv(
            [{"月份": "2026-03", "全新账户XYZ": "7777"}],
            fieldnames=["月份", "全新账户XYZ"],
        )
        resp = client.post(
            "/api/income/import/csv",
            files={"file": ("t.csv", csv_bytes, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        names = [a["name"] for a in accs]
        assert "全新账户XYZ" in names

    def test_import_skips_invalid_month(self, client, auth_headers):
        """月份格式不合法的行应被跳过。"""
        client.get("/api/income/accounts", headers=auth_headers)
        csv_bytes = make_csv(
            [{"月份": "not-a-month", "微众银行": "100"}],
            fieldnames=["月份", "微众银行"],
        )
        resp = client.post(
            "/api/income/import/csv",
            files={"file": ("t.csv", csv_bytes, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        result = resp.json()
        assert result["inserted"] == 0
        assert result["skipped"] >= 1

    def test_import_skips_negative_balance(self, client, auth_headers):
        """负数余额应被跳过。"""
        client.get("/api/income/accounts", headers=auth_headers)
        csv_bytes = make_csv(
            [{"月份": "2026-04", "微众银行": "-500"}],
            fieldnames=["月份", "微众银行"],
        )
        resp = client.post(
            "/api/income/import/csv",
            files={"file": ("t.csv", csv_bytes, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["skipped"] >= 1

    def test_import_ignores_total_column(self, client, auth_headers):
        """导入时应忽略「总资产」列，不将其当作账户名。"""
        client.get("/api/income/accounts", headers=auth_headers)
        csv_bytes = make_csv(
            [{"月份": "2026-05", "微众银行": "8888", "总资产": "8888"}],
            fieldnames=["月份", "微众银行", "总资产"],
        )
        resp = client.post(
            "/api/income/import/csv",
            files={"file": ("t.csv", csv_bytes, "text/csv")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        names = [a["name"] for a in accs]
        assert "总资产" not in names


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 导入-导出往返一致性（round-trip）
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoundTrip:

    def test_export_then_import_is_idempotent(self, client, auth_headers):
        """先录入数据 → 导出 CSV → 清空 → 重新导入 → 数据一致。"""
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        ids = [a["id"] for a in accs]

        original = {
            "2025-10": {ids[0]: 11111.11, ids[1]: 22222.22},
            "2025-11": {ids[0]: 33333.33, ids[2]: 44444.44},
        }
        for month, items in original.items():
            client.post(
                "/api/income/balances",
                json={"month": month, "balances": [{"account_id": k, "balance": v} for k, v in items.items()]},
                headers=auth_headers,
            )

        # 导出
        export_bytes = client.get("/api/income/export/csv", headers=auth_headers).content

        # 清空数据
        for month in original:
            client.delete(f"/api/income/balances/{month}", headers=auth_headers)

        # 重新导入
        client.post(
            "/api/income/import/csv",
            files={"file": ("export.csv", export_bytes, "text/csv")},
            headers=auth_headers,
        )

        # 验证
        for month, items in original.items():
            snapshot = client.get(f"/api/income/balances/{month}", headers=auth_headers).json()
            for acc_id, expected_balance in items.items():
                item = next((i for i in snapshot["items"] if i["account_id"] == acc_id), None)
                assert item is not None, f"账户 {acc_id} 在 {month} 中未找到"
                assert abs(item["balance"] - expected_balance) < 0.01, (
                    f"余额不一致: 期望 {expected_balance}, 实际 {item['balance']}"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. 趋势接口
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrend:

    def test_trend_returns_all_accounts_plus_total(self, client, auth_headers):
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        ids = [a["id"] for a in accs]
        for month in ["2025-11", "2025-12"]:
            client.post(
                "/api/income/balances",
                json={"month": month, "balances": [{"account_id": ids[0], "balance": 1000.0}]},
                headers=auth_headers,
            )
        resp = client.get("/api/income/stats/trend?months=6", headers=auth_headers)
        assert resp.status_code == 200
        account_ids = {a["account_id"] for a in resp.json()}
        assert 0 in account_ids  # 总资产折线

    def test_trend_empty_when_no_data(self, client, auth_headers):
        resp = client.get("/api/income/stats/trend", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_trend_total_equals_sum(self, client, auth_headers):
        """总资产折线的值应等于当月各账户余额之和。"""
        accs = client.get("/api/income/accounts", headers=auth_headers).json()
        ids = [a["id"] for a in accs]
        balances = [{"account_id": ids[0], "balance": 1000.0},
                    {"account_id": ids[1], "balance": 2000.0}]
        client.post(
            "/api/income/balances",
            json={"month": "2026-01", "balances": balances},
            headers=auth_headers,
        )
        resp = client.get("/api/income/stats/trend?months=12", headers=auth_headers)
        trend = {a["account_id"]: a["data"] for a in resp.json()}
        total_value = trend[0][0]["value"]
        assert abs(total_value - 3000.0) < 0.01
