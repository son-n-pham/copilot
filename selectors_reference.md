# Copilot Chat Automation - Selector Reference

This document provides the exact selectors from `workflow.md` that can be directly used in the CLI when running `playwright_copilot.py`.

## Quick Reference Table

| Action             | Command | Selector                                     | Description                  |
| ------------------ | ------- | -------------------------------------------- | ---------------------------- |
| Enter text prompt  | `input` | `role=combobox[name="Chat Input"]`           | Main chat input field        |
| Send message       | `click` | `role=button[name="Send"]`                   | Send button to submit prompt |
| New chat           | `click` | `role=button[name="New chat"]`               | Start new conversation       |
| Access file upload | `click` | `role=button[name="Add content and agents"]` | Open content menu            |
| Attach cloud files | `click` | `role=button[name="Attach cloud files"]`     | Open file picker             |
| Try GPT-5          | `click` | `role=button[name="Try GPT-5"]`              | Enable GPT-5 model           |
| Check GPT-5 status | `click` | `role=button[name="GPT-5 On"]`               | Verify GPT-5 is active       |

## Detailed Usage Examples

### 1. Basic Chat Flow

```
command> input
Enter text prompt: Analyze the uploaded files
Enter selector for text box [default: role=combobox[name="Chat Input"]]:
[Press Enter to use default]

command> click
Enter selector for button [default: role=button[name="Send"]]:
[Press Enter to use default]
```

### 2. Start New Chat

```
command> click
Enter selector for button [default: role=button[name="Send"]]: role=button[name="New chat"]
```

### 3. Enable GPT-5

```
command> click
Enter selector for button [default: role=button[name="Send"]]: role=button[name="Try GPT-5"]
```

### 4. File Upload Process

```
# Step 1: Open content menu
command> click
Enter selector for button [default: role=button[name="Send"]]: role=button[name="Add content and agents"]

# Step 2: Open file picker
command> click
Enter selector for button [default: role=button[name="Send"]]: role=button[name="Attach cloud files"]

# Step 3: Use the upload command with file names
command> upload
Enter file names (comma-separated): report.pdf, data.csv
```

## Default Values Set in Python File

The following default values have been set in the Python file:

- **Text input selector**: `role=combobox[name="Chat Input"]`
- **Button click selector**: `role=button[name="Send"]`

## File Picker Selectors (Used internally by upload command)

These selectors are hardcoded in the `upload_files_from_copilot_folder()` function:

| Element            | Selector                                       | Context       |
| ------------------ | ---------------------------------------------- | ------------- |
| Add content menu   | `role=button[name="Add content and agents"]`   | Main page     |
| Attach cloud files | `role=button[name="Attach cloud files"]`       | Main page     |
| File Picker iframe | `iframe[title="File Picker"]`                  | Main page     |
| My files button    | `role=button[name="My files"]`                 | Inside iframe |
| Copilot folder     | `role=link[name="copilot"]` (exact match)      | Inside iframe |
| File checkboxes    | `role=checkbox[name=<filename>]` (regex match) | Inside iframe |
| Select button      | `role=button[name="Select"]` (exact match)     | Inside iframe |

## Navigation Selectors

| Action            | Selector                 | Purpose                  |
| ----------------- | ------------------------ | ------------------------ |
| Go to current URL | Use `where` command      | Show current page URL    |
| Reload page       | Use `refresh` command    | Reload current page      |
| Navigate to URL   | Use `goto <url>` command | Navigate to specific URL |

## Response Monitoring Selectors (For future reference)

These selectors can be used to monitor Copilot responses:

| Element            | Selector                                                                        | Purpose                 |
| ------------------ | ------------------------------------------------------------------------------- | ----------------------- |
| Response container | `article` with `role=heading[name="Copilot said:"]`                             | Latest Copilot response |
| Loading indicators | Text matching `/Generating response\|Analyzing\|Working\|Reasoning\|Drafting/i` | Monitor completion      |
| Citation buttons   | `role=button[name=/popover for citation\|Reference\|Open .* popover/i]`         | Extract citations       |

## Best Practices

1. **Always use role-based selectors** - They are more reliable than CSS selectors
2. **Use exact matching for buttons** when multiple similar buttons exist
3. **Default selectors are pre-configured** - Just press Enter to use them
4. **File upload uses the `upload` command** - Don't use manual selectors for file operations
5. **Cross-origin iframe handling** is automatic in the upload function

## Troubleshooting

If a selector doesn't work:

1. Check if you're in the right context (main page vs iframe)
2. Verify the element is visible and interactable
3. Try using the browser's developer tools to inspect the element
4. Use the `where` command to confirm you're on the right page
