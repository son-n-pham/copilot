**Try GPT-5 button:**

- Robust selector: `getByRole('button', { name: 'Try GPT-5' })`
- When GPT-5 is active, the button may display as `getByRole('button', { name: 'GPT-5 On' })` and have `[active][pressed]` attributes.

**Plus button selector for "Add content and agents":**

- Robust selector: `getByTestId('PlusMenuButton')`
- Alternative robust selector: `button[ref=e72]` with visible text "Add content and agents"

The button was successfully clicked using `getByTestId('PlusMenuButton')`.

**Add content menu item selector:**

- Robust selector: `getByTestId('PlusMenuItemAttachContent')`
- Alternative robust selector: `menuitem[ref=e112]` with visible text "Add content"

The menu item was successfully clicked using `getByTestId('PlusMenuItemAttachContent')`.

**Attach cloud files button selector:**

- Robust selector: `getByTestId('upload-cloud-file')`
- Alternative robust selector: `button[ref=e276]` with visible text "Attach cloud files"

The button was successfully clicked using `getByTestId('upload-cloud-file')`.

**My files button selector:**

- Robust selector: `button[ref=f1e17]` with visible text "My files"
- Alternative robust selector: `getByRole('button', { name: 'My files' })` inside the file picker iframe

The button was successfully clicked using `button[ref=f1e17]` with visible text "My files".

**Copilot folder selector:**

- Robust selector: `link[ref=f1e1623]` with visible text "copilot"
- Alternative robust selector: `getByRole('link', { name: 'copilot' })` inside the file picker iframe

The folder was successfully clicked using `link[ref=f1e1623]` with visible text "copilot".

**Upload from local drive button selector:**


The button was successfully clicked using `getByTestId('upload-local-file')`. This action opens the file chooser modal, which can be handled by the "browser_file_upload" tool.

**File selection by file name (checkbox) selectors:**

- Robust selector for `time-depth curve.xlsx`: `getByRole('checkbox', { name: 'time-depth curve.xlsx' })` inside the file picker iframe
- Robust selector for `8.5-in_P505S_X38011.pdf`: `getByRole('checkbox', { name: '8.5-in_P505S_X38011.pdf' })` inside the file picker iframe

Both files were successfully selected using their respective robust selectors.

**General algorithm for robust file selection by file name:**

1. Locate the file picker iframe (if present).
2. Use `getByRole('checkbox', { name: '<file name>' })` to select the checkbox for the file with the exact name.
3. This approach is robust and works for any file as long as the file name is unique in the list.

**Universal robust selector for file selection by file name:**

- `getByRole('checkbox', { name: '<file name>' })` inside the file picker iframe

Replace `<file name>` with the exact file name you want to select. This selector works for any file in the file picker as long as the file name is unique.

**Select button in file picker:**

- Robust selector: `getByRole('button', { name: 'Select', exact: true })` inside the file picker iframe

The Select button was successfully clicked using this robust selector after choosing files.

**Chatbot input prompt field:**

Robust selector for prompt input textbox: `getByRole('combobox', { name: 'Chat Input' })` inside the main Copilot chat area


**Send button in Copilot chat area:**

Robust selector: `getByRole('button', { name: 'Send' })` inside the main Copilot chat area

**Start a New Chat button:**

- Robust selector: `getByRole('button', { name: 'New chat' })`
- If available: `getByTestId('newChatButton')`

This button starts a new chat session in the Copilot chat UI. It is typically located in the top action bar of the chat interface.

**Copilot chat response message selector:**

- Latest Copilot response (preferred):
	- `page.locator('article').filter({ has: page.getByRole('heading', { name: 'Copilot said:' }) }).last()`
- “Corresponding response” for a given user prompt (the Copilot reply that follows a specific “You said”):
	- Find the user’s article and select the next article with heading "Copilot said:" using a sibling hop.

Notes:
- Prefer Playwright locators over raw DOM queries for dynamic/virtualized content.
- Avoid brittle CSS like `ref=` or implementation-specific classnames.

Corresponding response (sibling) utility:

```javascript
// Returns the Copilot response article that immediately follows the given user prompt
async function getResponseForPrompt(page, promptText) {
	const youSaid = page
		.locator('article')
		.filter({ has: page.getByRole('heading', { name: 'You said:' }) })
		.filter({ hasText: promptText })
		.first();

	await youSaid.waitFor();

	// Hop to the next sibling article that has the Copilot heading
	const response = youSaid
		.locator('xpath=following-sibling::article[.//h6[normalize-space()="Copilot said:"]]')
		.first();

	await response.waitFor();
	return response;
}
```

Equality/validation refinement:
- When checking that the "corresponding" response matches the latest response, don't compare entire container text (it often includes banners/toolbars).
- Compare a scoped region instead, e.g., the first paragraph's text, or check for key phrases.
- Example:
```javascript
const latest = page
	.locator('article')
	.filter({ has: page.getByRole('heading', { name: 'Copilot said:' }) })
	.last();

const [pSibling, pLatest] = await Promise.all([
	sibling.locator('p, paragraph').first().innerText().catch(() => sibling.innerText()),
	latest.locator('p, paragraph').first().innerText().catch(() => latest.innerText()),
]);

// Use startsWith/includes rather than strict equality
const seemsSame = pSibling.trim().slice(0, 120) === pLatest.trim().slice(0, 120);
```

## Response Selector Validation Results

**Test Approach**: Sent second prompt "This is 2nd prompt for testing selector" to verify response extraction.

**Key Discovery**: Microsoft 365 Copilot Chat uses dynamic content loading where standard JavaScript DOM queries don't align with Playwright's page snapshot structure. Elements visible in snapshots (like `article[ref=e2552]`) aren't accessible through normal DOM selectors.

**Validated Response Elements**:
- Article e2503: "You said: This is 2nd prompt for testing selector"  
- Article e2552: "Copilot said: Got it! Your second prompt is noted..."

**Recommended Approach**: Use Playwright's text-based selectors for response extraction:
```javascript
// ✅ Text-based approach (more reliable)
page.getByText('Got it! Your second prompt is noted').first()
// or
page.locator('article').filter({ hasText: 'Copilot said:' }).last()

// ❌ DOM traversal approach (unreliable with dynamic content)
document.querySelectorAll('article')
```

**Rule to check if Copilot analysis is completed:**

- After selecting the response container (`div.fai-CopilotMessage[role='article']` with `<h6>` "Copilot said:"), check that its text does NOT include any of the following loading indicators:
	- "Generating response"
	- "Analyzing"
	- Other similar loading or progress phrases
- If these phrases are absent and the response contains the expected analysis content (tables, summaries, or closing prompts like "Let me know how you'd like to proceed!"), Copilot has finished and the answer is complete.