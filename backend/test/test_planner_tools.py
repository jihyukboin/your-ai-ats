import unittest
from unittest.mock import patch

import httpx

from app import planner_tools as tools


class PlannerToolsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(patch.object(tools, "_resource_cache", {}))
        self.enterContext(patch.object(tools, "_github_wait", {}))
        self.enterContext(patch.object(tools, "_backoff_until", 0))
        self.requests = []

    async def client(self, *responses):
        responses = iter(responses)

        def handle(request):
            self.requests.append(request)
            return next(responses)

        return await self.enterAsyncContext(httpx.AsyncClient(transport=httpx.MockTransport(handle)))

    async def test_registry_defines_arguments_outputs_and_failure_contract(self):
        specs = tools.tool_specs()
        self.assertEqual({s["name"] for s in specs}, {"search_candidates", "candidate_detail", "search_resources"})
        for spec in specs:
            self.assertEqual(spec["kind"], "external_api")
            self.assertTrue(spec["description"] and spec["input_schema"]["properties"])
            self.assertEqual(len(spec["output_schema"]["anyOf"]), 2)
            self.assertEqual((await tools.invoke_tool(spec["name"], {}))["error"]["code"], "INVALID_INPUT")
        self.assertEqual((await tools.invoke_tool("unregistered", {}))["error"]["code"], "UNKNOWN_TOOL")

    async def test_candidate_id_feeds_detail_and_preserves_unknown_measurements(self):
        results = {"items": [{"repository_url": tools.GITHUB + "/repos/test/repo", "number": 1, "title": "Docs"}],
                   "total_count": 1}
        issue = dict(title="Docs", state="open", labels=[dict(name="good first issue")], body=None, comments=None)
        client = await self.client(httpx.Response(200, json=results), httpx.Response(200, json=issue))
        found = (await tools.invoke_tool("search_candidates", {"language": "python"}, client=client))["data"]
        self.assertEqual(found["requested_date"], found["observed_date"])
        self.assertEqual(self.requests[0].url.params["page"], "1")
        self.assertFalse(found["has_more"])
        self.assertIn("is:public", self.requests[0].url.params["q"])
        args = {"id": found["items"][0]["id"]}
        self.assertEqual(args, {"id": "test/repo#1"})
        detail = (await tools.invoke_tool("candidate_detail", args, client=client))["data"]
        self.assertIsNone(detail["body_chars"])
        self.assertIsNone(detail["comments"])
        self.assertEqual(self.requests[1].url.path, "/repos/test/repo/issues/1")

    async def test_search_date_and_page(self):
        data = {"items": [{"repository_url": tools.GITHUB + "/repos/org/lib", "number": 31, "title": "FAQ"}],
                "total_count": 100, "incomplete_results": True}
        client = await self.client(httpx.Response(200, json=data))
        args = {"language": "c++", "page": 3, "reference_date": "2099-01-01"}
        response = (await tools.invoke_tool("search_candidates", args, client=client))["data"]
        self.assertTrue(response["has_more"])
        self.assertIn(response["observed_date"], response["note"])
        self.assertIn("2099-01-01", response["note"])
        self.assertIn("일부", response["note"])
        self.assertEqual(self.requests[0].url.params["page"], "3")

    async def test_no_results_and_empty_resource_cache(self):
        client = await self.client(httpx.Response(200, json={"items": []}), httpx.Response(200, json={"items": []}))
        for name in ["search_candidates", "search_resources", "search_resources"]:
            result = await tools.invoke_tool(name, {"language": "none"}, client=client)
            self.assertEqual(result["error"]["code"], "NO_RESULT")
        self.assertEqual(len(self.requests), 2)

    async def test_terms_and_provider_throttling(self):
        row = dict(title="R&amp;D", link="https://stackoverflow.com/q/1", owner=dict(display_name="Lee", link="https://stackoverflow.com/users/7"),
                   content_license="CC BY-SA 4.0")
        client = await self.client(httpx.Response(200, json=dict(items=[row], backoff=5)))
        found = (await tools.invoke_tool("search_resources", {"language": "go"}, client=client))["data"]
        self.assertEqual(found["items"][0], dict(name="R&D", url=row["link"], author="Lee", author_url=row["owner"]["link"], license="CC BY-SA 4.0"))
        self.assertEqual(found, (await tools.invoke_tool("search_resources", {"language": "GO"}, client=client))["data"])
        refused = await tools.invoke_tool("search_resources", {"language": "java"}, client=client)
        self.assertEqual(refused["error"]["code"], "RATE_LIMIT")
        self.assertEqual(len(self.requests), 1)

    async def test_tool_failures_hide_provider_details(self):
        for name, inputs, status, code in [
            ("candidate_detail", {"id": "org/repo#3"}, 404, "NOT_FOUND"),
            ("candidate_detail", {"id": "org/repo#3"}, 401, "AUTH_ERROR"),
            ("search_candidates", {"language": "go"}, 503, "UPSTREAM_ERROR"),
            ("search_resources", {"language": "go"}, 429, "RATE_LIMIT"),
            ("search_candidates", {"language": "go"}, 429, "RATE_LIMIT"),
        ]:
            client = await self.client(httpx.Response(status, text="private upstream diagnostic"))
            result = await tools.invoke_tool(name, inputs, client=client)
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], code)
            self.assertNotIn("private", str(result))
        refused = await tools.invoke_tool("search_candidates", {"language": "go"}, client=client)
        self.assertEqual(refused["error"]["code"], "RATE_LIMIT")
        self.assertEqual(len(self.requests), 5)

    async def test_invalid_identifiers_and_closed_issue(self):
        client = await self.client(httpx.Response(200, json={"state": "closed"}))
        for invalid in ["org/..#3", "https://example.org/1", "../x#3", "owner/repo#-1"]:
            result = await tools.invoke_tool("candidate_detail", {"id": invalid}, client=client)
            self.assertEqual(result["error"]["code"], "INVALID_INPUT")
        closed = await tools.invoke_tool("candidate_detail", {"id": "org/repo#11"}, client=client)
        self.assertEqual(closed["error"]["code"], "NO_RESULT")
        self.assertEqual(len(self.requests), 1)
