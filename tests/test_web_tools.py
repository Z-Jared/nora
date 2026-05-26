import unittest

from mini_agent.web_tools import WebTools, _html_to_text, _extract_duckduckgo_results


class HtmlToTextTests(unittest.TestCase):
    def test_strips_script_and_style_tags(self):
        html = '<p>Hello<script>alert("xss")</script><style>.a{}</style></p>'

        result = _html_to_text(html)

        self.assertNotIn("alert", result)
        self.assertNotIn(".a{}", result)
        self.assertIn("Hello", result)

    def test_converts_br_and_p_to_newlines(self):
        html = "line1<br>line2<br/>line3<p>line4</p>"

        result = _html_to_text(html)

        self.assertIn("line1", result)
        self.assertIn("line2", result)
        self.assertIn("line4", result)

    def test_unescapes_html_entities(self):
        html = "<p>&amp; &lt; &gt; &quot;</p>"

        result = _html_to_text(html)

        self.assertIn("&", result)
        self.assertIn("<", result)
        self.assertIn(">", result)

    def test_collapses_whitespace(self):
        html = "<p>  hello   world  </p>"

        result = _html_to_text(html)

        self.assertNotIn("   ", result)
        self.assertIn("hello world", result)

    def test_strips_all_html_tags(self):
        html = '<div class="test"><a href="url">link</a></div>'

        result = _html_to_text(html)

        self.assertNotIn("<", result)
        self.assertNotIn(">", result)
        self.assertIn("link", result)


class ExtractDuckduckgoResultsTests(unittest.TestCase):
    def test_extracts_results_from_html(self):
        html = '''
        <a class="result__a" href="https://example.com/page">Example Title</a>
        <a class="result__a" href="https://other.com/test">Other Title</a>
        '''

        results = _extract_duckduckgo_results(html, max_results=5)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "Example Title")
        self.assertIn("example.com", results[0][1])

    def test_unwraps_uddg_redirect(self):
        html = '<a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage">Title</a>'

        results = _extract_duckduckgo_results(html, max_results=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], "https://example.com/page")

    def test_respects_max_results(self):
        html = ''.join(
            f'<a class="result__a" href="https://example.com/{i}">Title {i}</a>'
            for i in range(10)
        )

        results = _extract_duckduckgo_results(html, max_results=3)

        self.assertEqual(len(results), 3)

    def test_returns_empty_for_no_matches(self):
        results = _extract_duckduckgo_results("<p>no results here</p>", max_results=5)

        self.assertEqual(results, [])


class WebToolsFetchTests(unittest.TestCase):
    def test_rejects_non_http_url(self):
        tools = WebTools(fetcher=lambda url, timeout: "")

        result = tools.fetch_url("file:///etc/passwd")

        self.assertIn("拒绝访问", result)

    def test_rejects_private_url(self):
        tools = WebTools(fetcher=lambda url, timeout: "")

        result = tools.fetch_url("http://127.0.0.1:8000")

        self.assertIn("拒绝访问", result)

    def test_wraps_result_in_untrusted_tags(self):
        def fake_fetcher(url, timeout):
            return "<html><body>Hello world</body></html>"

        tools = WebTools(fetcher=fake_fetcher)

        result = tools.fetch_url("https://example.com")

        self.assertIn("<untrusted_source", result)
        self.assertIn("Hello world", result)
        self.assertIn("</untrusted_source>", result)

    def test_handles_fetch_error(self):
        def failing_fetcher(url, timeout):
            raise ConnectionError("timeout")

        tools = WebTools(fetcher=failing_fetcher)

        result = tools.fetch_url("https://example.com")

        self.assertIn("网页读取失败", result)

    def test_truncates_long_content(self):
        long_text = "x" * 20000

        def fake_fetcher(url, timeout):
            return long_text

        tools = WebTools(fetcher=fake_fetcher)

        result = tools.fetch_url("https://example.com", max_chars=500)

        self.assertLess(len(result), 20000)


class WebToolsSearchTests(unittest.TestCase):
    def test_empty_query_returns_hint(self):
        tools = WebTools(fetcher=lambda url, timeout: "")

        result = tools.web_search("")

        self.assertIn("请提供搜索关键词", result)

    def test_handles_search_error(self):
        def failing_fetcher(url, timeout):
            raise ConnectionError("fail")

        tools = WebTools(fetcher=failing_fetcher)

        result = tools.web_search("test query")

        self.assertIn("网页搜索失败", result)

    def test_returns_no_results_message(self):
        def empty_fetcher(url, timeout):
            return "<html>no results</html>"

        tools = WebTools(fetcher=empty_fetcher)

        result = tools.web_search("obscure query")

        self.assertIn("没有找到搜索结果", result)

    def test_returns_formatted_results(self):
        ddg_html = '''
        <a class="result__a" href="https://example.com/page">Example Result</a>
        '''

        def fake_fetcher(url, timeout):
            return ddg_html

        tools = WebTools(fetcher=fake_fetcher)

        result = tools.web_search("test")

        self.assertIn("<untrusted_source", result)
        self.assertIn("Example Result", result)
        self.assertIn("example.com", result)


if __name__ == "__main__":
    unittest.main()
