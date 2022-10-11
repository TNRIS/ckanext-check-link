from unittest.mock import ANY

import ckan.plugins.toolkit as tk
import pytest
from pytest_httpx import HTTPXMock

# from aioresponses import aioresponses
from ckan.tests.helpers import call_action


@pytest.fixture
def rmock(httpx_mock):
    return httpx_mock


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestUrl:
    def test_allow_multi_url_validatoin(self, faker, rmock):
        url1 = faker.url()
        url2 = faker.url()

        # rmock.head(url1, status=200)
        # rmock.head(url2, status=404)
        rmock.add_response(url=url1, status_code=200, method="HEAD")
        rmock.add_response(url=url2, status_code=404, method="HEAD")

        result = call_action("check_link_url_check", url=[url1, url2])

        assert result == [
            {
                "code": 200,
                "explanation": ANY,
                "reason": ANY,
                "state": "available",
                "url": url1,
            },
            {
                "code": 404,
                "explanation": ANY,
                "reason": ANY,
                "state": "missing",
                "url": url2,
            },
        ]

    def test_not_saved_by_defaut(self, faker, rmock):
        url = faker.url()

        # rmock.head(url, status=200)
        rmock.add_response(url=url, status_code=200, method="HEAD")

        call_action("check_link_url_check", url=url)

        with pytest.raises(tk.ObjectNotFound):
            call_action("check_link_report_show", url=url)

    def test_can_be_saved(self, faker, rmock):
        url = faker.url()

        # rmock.head(url, status=200)
        rmock.add_response(url=url, status_code=200, method="HEAD")

        call_action("check_link_url_check", url=url, save=True)
        report = call_action("check_link_report_show", url=url)
        assert report == {
            "last_checked": ANY,
            "details": {
                "code": 200,
                "explanation": "Link is available",
                "reason": "OK",
            },
            "id": ANY,
            "resource_id": None,
            "package_id": None,
            "state": "available",
            "url": url,
        }


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestResource:
    def test_not_saved_by_defaut(self, resource, rmock):
        # rmock.head(resource["url"], status=200)
        rmock.add_response(url=resource["url"], status_code=200, method="HEAD")
        call_action("check_link_resource_check", id=resource["id"])

        with pytest.raises(tk.ObjectNotFound):
            call_action("check_link_report_show", resource_id=resource["id"])

    def test_can_be_saved(self, resource, rmock):
        # rmock.head(resource["url"], status=200)
        rmock.add_response(url=resource["url"], status_code=200, method="HEAD")
        call_action("check_link_resource_check", id=resource["id"], save=True)
        report = call_action("check_link_report_show", resource_id=resource["id"])
        assert report["resource_id"] == resource["id"]
        assert report["package_id"] == resource["package_id"]


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestPackage:
    def test_basic(self, resource_factory, rmock, package):
        resource = resource_factory(package_id=package["id"])
        # rmock.head(resource["url"], status=200)
        rmock.add_response(url=resource["url"], status_code=200, method="HEAD")
        result = call_action("check_link_package_check", id=package["id"])
        assert len(result) == 1
        assert result[0]["code"] == 200

    def test_empty(self, package):
        result = call_action("check_link_package_check", id=package["id"])
        assert result == []
