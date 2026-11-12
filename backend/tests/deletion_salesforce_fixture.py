from app.salesforce.client import SalesforceError

LEAD = "00Q000000000001AAA"
ORG = "00D000000000001AAA"


class DeletionSalesforce:
    origin = "https://sample.my.salesforce.com"

    def __init__(self, row):
        self.row = row
        self.deletes = []
        self.unavailable = False
        self.timeout_after_delete = False
        self.cascade = False

    def close(self):
        pass

    def query(self, soql):
        if self.unavailable:
            raise SalesforceError("Test unavailable")
        if "FROM Organization" in soql:
            return [{"Id": ORG}]
        return [{"Id": "related"}] if self.cascade else []

    def request(self, method, path, **kwargs):
        if self.unavailable:
            raise SalesforceError("Test unavailable")
        if path.endswith("queryAll"):
            assert f"WHERE Id = '{LEAD}'" in kwargs["params"]["q"]
            return {"done": True, "records": [self.row] if self.row else []}
        if path.endswith("describe"):
            return {
                "deletable": True,
                "childRelationships": [
                    {"cascadeDelete": True, "childSObject": "Task", "field": "WhoId"}
                ],
            }
        assert method == "DELETE" and path.endswith("/Lead/" + LEAD)
        self.deletes.append(LEAD)
        self.row["IsDeleted"] = True
        if self.timeout_after_delete:
            self.timeout_after_delete = False
            raise SalesforceError("Test ambiguous timeout")
        return {}
