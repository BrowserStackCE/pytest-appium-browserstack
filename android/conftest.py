import pytest
from browserstack.local import Local
import os
from appium import webdriver
import json
from jsonmerge import merge
from browsermobproxy import Server
import psutil
import time

CONFIG_FILE = os.environ['CONFIG_FILE'] if 'CONFIG_FILE' in os.environ else 'run-single-test/single.json'
TASK_ID = int(os.environ['TASK_ID']) if 'TASK_ID' in os.environ else 0

with open(CONFIG_FILE) as data_file:
    CONFIG = json.load(data_file)

bs_local = None
proxy = None

BROWSERSTACK_USERNAME = os.environ['BROWSERSTACK_USERNAME'] if 'BROWSERSTACK_USERNAME' in os.environ else CONFIG["user"]
BROWSERSTACK_ACCESS_KEY = os.environ['BROWSERSTACK_ACCESS_KEY'] if 'BROWSERSTACK_ACCESS_KEY' in os.environ else CONFIG[
    "key"]


def start_local(proxy_port):
    """Code to start browserstack local before start of test."""
    global bs_local
    bs_local = Local()
    bs_local_args = {
        "key": BROWSERSTACK_ACCESS_KEY or "access_key", "forcelocal": "true", "forceproxy": "true",
        "localProxyHost": "localhost", "localProxyPort": str(proxy_port), "v": "true", "force": "true"}
    print("port passed in local is", proxy_port)
    bs_local.start(**bs_local_args)


def stop_local():
    """Code to stop browserstack local after end of test."""
    global bs_local
    if bs_local is not None:
        bs_local.stop()


@pytest.fixture(scope='session')
def session_capabilities():
    capabilities = merge(CONFIG['environments']
                         [TASK_ID], CONFIG["capabilities"])
    capabilities['bstack:options']['userName'] = BROWSERSTACK_USERNAME
    capabilities['bstack:options']['accessKey'] = BROWSERSTACK_ACCESS_KEY
    for proc in psutil.process_iter():
        # check whether the process name matches
        if proc.name() == "browsermob-proxy":
            proc.kill()

    dict = {'port': 8156}
    server = Server(path="/Users/manyaasokan/Downloads/browsermob-proxy-2.1.4/bin/browsermob-proxy", options=dict)
    server.start()
    time.sleep(1)
    proxy = server.create_proxy()
    time.sleep(2)
    proxy_port = proxy.port

    if "local" in capabilities['bstack:options'] and capabilities['bstack:options']['local']:
        start_local(proxy_port)

    return proxy, capabilities


@pytest.fixture(scope='function')
def setWebdriver(request, session_capabilities):
    remoteURL = "https://hub.browserstack.com/wd/hub"
    proxy, session_capabilities = session_capabilities
    driver = webdriver.Remote(remoteURL, session_capabilities)
    proxy.new_har("test_app")

    if hasattr(proxy, 'port') and proxy.port:
        print(f"Proxy is running on port: {proxy.port}")
    request.cls.driver = driver

    yield driver
   # Get the har logs
    har_data = proxy.har
    entries = har_data['log']['entries']
    for entry in entries:
        print(entry['request']['url'])

    # Save the HAR to a file
    with open('output.har', 'w') as har_file:
        json.dump(har_data, har_file)

    driver.quit()


def pytest_sessionfinish(session, exitstatus):
    stop_local()
