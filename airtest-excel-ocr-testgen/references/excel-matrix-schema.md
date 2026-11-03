# Excel Test Matrix Schema & Action Grammar

This specification defines the standard column structure and action syntax for parsing manual QA test checklists into automated Airtest scripts.

---

## 1. Standard Column Mapping

The generator inspects Excel sheets and maps columns based on standard header aliases (case-insensitive):

| Canonical Key | Supported Header Aliases | Description | Example |
| :--- | :--- | :--- | :--- |
| **`id`** | `Test ID`, `TC_ID`, `Case ID`, `ID` | Unique identifier for the test case | `TC_LOGIN_001` |
| **`feature`** | `Module`, `Feature`, `Screen`, `Category` | Game subsystem or screen being verified | `Shop`, `Battle`, `Setting` |
| **`precondition`** | `Pre-condition`, `Setup`, `Initial State` | Game state required before executing | `Account Level >= 5`, `In Lobby` |
| **`action`** | `Step`, `Action`, `Steps`, `Procedure` | Single or multi-line gameplay actions | `Tap "PLAY"`, `Wait 3s` |
| **`target`** | `Target`, `Element`, `Button`, `UI Component` | Target button text, sprite name, or coordinate | `btn_battle.png`, `"CLAIM"` |
| **`expected`** | `Expected Result`, `Expected`, `Verification` | State or UI verified after actions | `See "VICTORY"`, `assert_exists` |

---

## 2. Action Grammar & Syntax

The generator parses natural language and semi-structured steps in the `action` and `expected` columns into Airtest commands:

### Interaction Commands

| Action Syntax | Parsed Airtest Command | Resolution Strategy |
| :--- | :--- | :--- |
| `Tap "<TEXT>"` / `Click "<TEXT>"` | `touch_text("<TEXT>")` | **OCR**: Scans screen for `<TEXT>`, computes center coordinates, and taps. |
| `Tap <image.png>` | `touch(Template("<image.png>"))` | **Template**: Matches image template sprite against screen. |
| `Tap at (x, y)` | `touch((x, y))` | **Coordinate**: Directly touches relative or absolute coordinate. |
| `Swipe <UP|DOWN|LEFT|RIGHT>` | `swipe_vector("<DIRECTION>")` | **Gesture**: Swipes in specified direction across screen center. |
| `Wait <N>s` / `Sleep <N>` | `sleep(<N>)` | **Timing**: Pauses execution for $N$ seconds. |
| `Input "<TEXT>"` | `text("<TEXT>")` | **Keyboard**: Types text into currently focused input box. |
| `Back` / `Key BACK` | `keyevent("BACK")` | **Keycode**: Triggers Android/System Back button. |

### Verification & Assertion Commands

| Expected Syntax | Parsed Airtest Command | Description |
| :--- | :--- | :--- |
| `See "<TEXT>"` / `Assert Text "<TEXT>"` | `assert_text("<TEXT>")` | Uses OCR to assert text is visible on screen. |
| `See <image.png>` / `Assert <image.png>` | `assert_exists(Template("<image.png>"))` | Asserts image template is visible on screen. |
| `Not See "<TEXT>"` | `assert_not_text("<TEXT>")` | Asserts text has disappeared. |
| `Not See <image.png>` | `assert_not_exists(Template("<image.png>"))` | Asserts image template is not present. |

---

## 3. Multi-Step Notation

If multiple steps are written in a single cell, separate them with numbers or newlines:

```text
1. Tap "Shop"
2. Wait 2s
3. Swipe LEFT
4. Tap "Buy 100 Gems"
```

The parser splits each line, resolves target UI types, and compiles them into sequential python statements within the generated test function.
