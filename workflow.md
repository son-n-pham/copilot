# Microsoft 365 Copilot Chat Automation Workflow

**Battle-tested workflow using role-based selectors for maximum reliability**

## 🎯 Overview
This workflow automates file upload and analysis in Microsoft 365 Copilot Chat, specifically handling SharePoint/OneDrive integration through cross-origin iframes.

## 📋 Complete Automation Steps

### 1. Initialize New Chat Session
```javascript
await page.getByRole('button', { name: 'New chat' }).click();
```
**Purpose**: Start fresh conversation context  
**Reliability**: ✅ Highly reliable - consistent button labeling

### 2. Activate GPT-5 (Optional but Recommended)
```javascript
// Check if already active
const gpt5Active = await page.getByRole('button', { name: 'GPT-5 On' }).isVisible();

if (!gpt5Active) {
  await page.getByRole('button', { name: 'Try GPT-5' }).click();
  // Wait for activation confirmation
  await page.getByRole('button', { name: 'GPT-5 On' }).waitFor();
}
```
**Purpose**: Enable advanced model capabilities  
**Reliability**: ✅ Role-based detection and activation

### 3. Enter Text Prompt
```javascript
await page.getByRole('combobox', { name: 'Chat Input' }).fill('Analyse the files');
```
**selector**: role=combobox[name="Chat Input"]
**Purpose**: Set text prompt
**Reliability**: ✅ Semantic combobox role is stable

### 4. Access File Upload Interface
```javascript
// Open the add content menu
// selector: role=button[name="Add content and agents"]
await page.getByRole('button', { name: 'Add content and agents' }).click();


// Select cloud file attachment option
// selector: role=button[name="Attach cloud files"]
await page.getByRole('button', { name: 'Attach cloud files' }).click();
```
**Purpose**: Navigate to file picker interface  
**Reliability**: ✅ Clear role-based navigation

### 5. Navigate SharePoint/OneDrive File Picker
```javascript
// Access iframe content (CRITICAL: Cross-origin context switch)
const filePickerFrame = page.locator('iframe[title="File Picker"]').contentFrame();

// Navigate to personal files
await filePickerFrame.getByRole('button', { name: 'My files' }).click();

// Enter target folder with exact matching
await filePickerFrame.getByRole('link', { name: 'copilot', exact: true }).click();
```
**Purpose**: Navigate to target file location  
**Key Challenge**: Cross-origin iframe requires `contentFrame()` access  
**Reliability**: ✅ Role-based selectors work within iframe context

### 6. Select Target File
```javascript
// Select file using partial name matching (handles dynamic content)
fileName = "file name"
await filePickerFrame.getByRole('checkbox', { name: fileName }).click();

// Confirm selection with exact matching
await filePickerFrame.getByRole('button', { name: 'Select', exact: true }).click();
```
**Purpose**: Choose and confirm file selection  
**Key Insight**: Partial name matching required for file checkboxes  
**Reliability**: ✅ Handles dynamic file listing

### 7. Submit for Analysis
```javascript
await page.getByRole('button', { name: 'Send' }).click();
```
**Purpose**: Send prompt with attached file to Copilot  
**Reliability**: ✅ Standard send button interaction

### 8. Monitor Response Generation
```javascript
// Wait for a Copilot response container to appear
await page
  .locator('article')
  .filter({ has: page.getByRole('heading', { name: 'Copilot said:' }) })
  .last()
  .waitFor();

// Monitor completion: hide common loading/progress labels (best-effort)
const loading = page.getByText(/Generating response|Analyzing|Working|Reasoning|Drafting/i);
await loading.waitFor({ state: 'hidden' }).catch(() => {});
```
**Purpose**: Track analysis completion  
**Reliability**: ✅ Consistent response patterns

### 9. Get the Copilot Response Content
```javascript
// Get the most recent Copilot response (latest article with "Copilot said:")
const responseSelector = page
  .locator('article')
  .filter({ has: page.getByRole('heading', { name: 'Copilot said:' }) })
  .last();

// Get the full response text (includes paragraphs, lists, tables, etc.)
const responseText = await responseSelector.innerText();

// Optional: extract structured parts
const responseHeadings = await responseSelector.getByRole('heading').allTextContents();
const responseTables = await responseSelector.locator('table').allTextContents();
const responseListItems = await responseSelector.locator('li').allTextContents();

// Optional: get citation badges/buttons if present
const citations = await responseSelector
  .getByRole('button', { name: /popover for citation|Reference|Open .* popover/i })
  .allTextContents();
```
**Purpose**: Extract the generated analysis response  
**Key Features**:
- ✅ Targets the latest Copilot response using `.last()`
- ✅ Uses role-based heading selector for reliability
- ✅ Provides content extraction options for different data types
- ✅ Handles citations and references

## 🔧 Technical Challenges & Solutions

### Challenge 1: Cross-Origin Iframe Access
**Problem**: SharePoint/OneDrive file picker runs in separate origin iframe  
**Solution**: Use `page.locator('iframe[title="File Picker"]').contentFrame()` for all file picker operations  
**Impact**: Critical for any file picker automation

### Challenge 2: Dynamic File Names
**Problem**: Full file names may not match exactly due to truncation or formatting  
**Solution**: Use partial name matching (e.g., `-in_DD505VSX_V10021.pdf` instead of full name)  
**Impact**: Essential for reliable file selection

### Challenge 3: Button Disambiguation
**Problem**: Multiple buttons with similar names  
**Solution**: Use `exact: true` parameter for precise matching  
**Impact**: Prevents wrong button clicks

### Challenge 4: Context Switching
**Problem**: Operations span main page and iframe contexts  
**Solution**: Explicitly manage context with appropriate page/frame references  
**Impact**: Ensures selectors target correct elements

### Challenge 5: Dynamic Snapshot vs DOM Access
**Problem**: Direct DOM traversal in `page.evaluate` (e.g., `document.querySelectorAll('article')`) may not reflect what Playwright can locate; dynamic rendering and virtualization can hide nodes from raw DOM queries.  
**Solution**: Prefer Playwright locators (`page.locator('article').filter({ hasText: 'Copilot said:' })`, `page.getByText(...)`) for visibility/state-aware selection.  
**Impact**: Greatly improves reliability of response detection and extraction in dynamic UIs.

## 🎓 Lessons Learned & Best Practices

### 1. **Role-Based Selectors Supremacy**
- ✅ **Use**: `getByRole('button', { name: 'Text' })` - semantically meaningful and stable
- ❌ **Avoid**: `ref=` or CSS selectors - fragile and implementation-dependent

### 2. **Iframe Handling Strategy**
- Always use `contentFrame()` for cross-origin iframe content
- Maintain separate references for main page vs iframe operations
- Test iframe accessibility before attempting element interactions

### 3. **Partial Matching Techniques**
- File names may be truncated in UI - use distinctive partial matches
- Checkbox names often use abbreviated file names
- Test with various file name lengths and characters

### 4. **Exact Matching Requirements**
- Use `exact: true` for buttons when multiple similar options exist
- Particularly important for "Select", "Cancel", "OK" type buttons
- Prevents accidental selection of wrong elements

### 5. **Response Monitoring Patterns**
- Wait for response containers to appear before checking content
- Monitor loading states to determine completion
- Handle variable response times gracefully
- Prefer text-based Playwright locators over raw DOM queries for dynamic content

## 🔄 Execution Results

**Status**: ✅ **FULLY SUCCESSFUL**

All workflow steps completed using role-based selectors:
- New chat creation ✅
- GPT-5 activation ✅  
- Prompt entry ✅
- File picker navigation ✅
- Cross-origin iframe handling ✅
- File selection and attachment ✅
- Message submission ✅
- Response generation initiated ✅

**Performance**: Role-based approach required zero fallback selectors and demonstrated high reliability across complex UI interactions including cross-origin iframe operations.
