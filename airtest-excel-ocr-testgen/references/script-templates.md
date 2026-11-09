# Standard Airtest Script Templates with Self-Healing

This document provides reference templates used by the generator to create runnable, self-healing Airtest automation test scripts.

---

## 1. Single Test Case Template (`test_<case_id>.py`)

```python
# -*- coding: utf-8 -*-
"""
Generated Airtest Script: {test_id} - {feature}
Source Checklist: {source_file}
"""

import sys
import time
import logging
from airtest.core.api import (
    init_device,
    connect_device,
    start_app,
    stop_app,
    touch,
    swipe,
    sleep,
    text,
    keyevent,
    snapshot,
    Template,
    assert_exists,
    assert_not_exists,
    G
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("{test_id}")

PACKAGE_NAME = "{package_name}"
DEVICE_URI = "{device_uri}"

def dismiss_popups():
    """Dismisses known blocking popups (Close X, Later, Skip)."""
    close_buttons = [
        Template(r"tpl_btn_close_x.png", threshold=0.8),
        Template(r"tpl_btn_skip.png", threshold=0.8)
    ]
    for btn in close_buttons:
        if btn.filepath and exists(btn):
            logger.info("Dismissing blocking popup...")
            touch(btn)
            sleep(1)

def run_step(step_name: str, action_fn, *args, **kwargs):
    """Executes a step with automatic popup guard and timing."""
    logger.info(f"==> STEP: {step_name}")
    dismiss_popups()
    res = action_fn(*args, **kwargs)
    sleep(1)
    return res

def setup():
    """Initializes device and starts the game."""
    logger.info("Setting up device and launching package...")
    if not G.DEVICE:
        init_device("Android") if not DEVICE_URI else connect_device(DEVICE_URI)
    start_app(PACKAGE_NAME)
    sleep(5)
    dismiss_popups()

def teardown():
    """Collects state and tears down."""
    logger.info("Tearing down test case...")
    snapshot(filename=f"report_{test_id}_final.png", msg="Final Screen")
    # stop_app(PACKAGE_NAME)

def {test_function_name}():
    """
    {test_id}: {test_description}
    Precondition: {precondition}
    """
    try:
        setup()
        
        # --- Generated Steps ---
{generated_steps}

        logger.info("==> Test Case {test_id} PASSED 100%")
    except Exception as e:
        logger.error(f"==> Test Case {test_id} FAILED: {{e}}")
        snapshot(filename=f"error_{test_id}.png", msg=f"Failure: {{e}}")
        raise
    finally:
        teardown()

if __name__ == "__main__":
    {test_function_name}()
```

---

## 2. Multi-Test Runner Template (`test_suite_runner.py`)

For executing an entire module or sheet of test cases in sequence:

```python
import unittest
from airtest.core.api import auto_setup

class GameTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        auto_setup(__file__)

    # Test cases injected here:
    # def test_01_login(self): ...
    # def test_02_shop_purchase(self): ...

if __name__ == "__main__":
    unittest.main()
```
