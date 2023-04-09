from django.test import RequestFactory
from django.test import override_settings

from django_forbid.access import grants_access
from django_forbid.detect import detect_vpn

LOCALHOST = "localhost"
IP_LONDON = "212.102.63.59"
IP_ZURICH = "146.70.99.178"


class SessionStore(dict):
    def has_key(self, key):
        return key in self


class WSGIRequest:
    def __init__(self, accept):
        self.accept = accept
        self.session = SessionStore()

    def get(self):
        request = RequestFactory().get("/")
        request.session = self.session
        request.META["HTTP_ACCEPT"] = self.accept
        return request

    def post(self, data):
        request = RequestFactory().post("/", data)
        request.session = self.session
        request.META["HTTP_ACCEPT"] = self.accept
        return request


class Detector:
    def __init__(self, get_response, ajax=False):
        access = "*/*" if ajax else "text/html"
        self.request = WSGIRequest(access)
        self.get_response = get_response

    def request_resource(self, ip_address=""):
        """Sends a request to the server to access a resource"""
        request = self.request.get()
        grants_access(request, ip_address)
        return detect_vpn(self.get_response, request)

    def request_access(self):
        """Simulates the request sent by the user browser to the server"""
        request = self.request.post({"timezone": "Europe/London"})
        return detect_vpn(self.get_response, request)


@override_settings(FORBID_VPN=True)
def test_detect_when_using_localhost(get_response):
    """It should give access to the user when using localhost"""
    detector = Detector(get_response)
    response = detector.request_resource(LOCALHOST)
    assert response.status_code == 200


@override_settings(FORBID_VPN=True)
def test_detect_when_using_localhost_ajax(get_response):
    """It should give access to the user when request is done by AJAX"""
    detector = Detector(get_response, True)
    response = detector.request_resource(LOCALHOST)
    assert response.status_code == 200


@override_settings(FORBID_VPN=True)
def test_detect_when_using_nonlocal_ip(get_response):
    """User should pass through two requests to access the resource"""
    detector = Detector(get_response)
    response = detector.request_resource(IP_LONDON)
    assert response.status_code == 302
    response = detector.request_access()
    assert response.status_code == 200


@override_settings(FORBID_VPN=True)
def test_detect_when_using_vpn(get_response):
    """User should be forbidden to access the resource when using VPN"""
    detector = Detector(get_response)
    response = detector.request_resource(IP_ZURICH)
    assert response.status_code == 302
    response = detector.request_access()
    assert response.status_code == 403


@override_settings(FORBID_VPN=True)
def test_detect_when_turns_off_vpn_after_using(get_response):
    """User should get access to the resource when VPN is turned off"""
    detector = Detector(get_response)
    response = detector.request_resource(IP_ZURICH)
    assert response.status_code == 302
    response = detector.request_access()
    assert response.status_code == 403

    # Turn off VPN - back to London
    detector = Detector(get_response)
    response = detector.request_resource(IP_LONDON)
    assert response.status_code == 302
    response = detector.request_access()
    assert response.status_code == 200


@override_settings(FORBID_VPN=True)
def test_detect_when_using_nonlocal_ip_ajax(get_response):
    """It should give access to the user when request is done by AJAX"""
    detector = Detector(get_response, True)
    response = detector.request_resource(IP_LONDON)
    assert response.status_code == 200
