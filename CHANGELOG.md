# Changelog

## [3.0.0] - 2025-08-25

### 🤖 **Multi-Model Summarization System**
- **Dual-model approach**: Generate two independent summaries using different LLM models
- **Intelligent synthesis**: Third model analyzes both summaries and original transcript to create optimal final summary
- **Flexible model configuration**: Mix different model types (GPT, Claude, etc.) for optimal results
- **Fallback strategies**: Graceful degradation with configurable fallback options (best_summary, primary_summary, single_model)
- **Cost optimization**: Smart model selection balancing quality and efficiency
- **Token tracking**: Comprehensive monitoring of token usage across all three model calls
- **Backward compatibility**: Existing channels continue using single-model unless explicitly configured

### 🎯 **Enhanced QnA System with RAG**
- **Channel-specific conversations**: Chat with individual channel databases without cross-contamination
- **Video tagging**: Tag specific videos in Telegram for targeted questioning with full context
- **Persistent chat context**: Maintains conversation history for meaningful ongoing discussions
- **Smart retrieval**: RAG searches through video titles, descriptions, and cleaned subtitles
- **Context window management**: Intelligent handling of long conversations
- **Citation support**: Answers cite which videos information came from

### 🏗️ **Architecture Improvements**
- **Service-oriented design**: New MultiModelLLMService extends existing LLMService
- **Template system**: Dedicated synthesis templates with creator context extraction
- **Model configuration**: Structured ModelConfig and TokenUsage tracking
- **Error handling**: Comprehensive fallback mechanisms and error recovery

### 📚 **Documentation Updates**
- **README.md**: Added multi-model and QnA system documentation
- **Configuration examples**: Complete YAML examples for new features
- **Migration guide**: Clear instructions for adopting new features
- **Architecture notes**: Updated technical documentation

## [2.2.0] - 2025-08-19

### 🎨 **Enhanced Structured Logging System**
- **Rich-based logging**: Replaced standard Python logging with Rich for beautiful terminal output
- **Semantic color coding**: Intuitive colors for different data types
  - Channel names: Red (easy identification)
  - Video titles: Green (content highlighting)
  - Success counts: Green (positive metrics)
  - Failed counts: Red (negative metrics)
  - Errors: Bright red (problem indication)
  - General counts: Yellow (neutral metrics)
- **LoggerFactory pattern**: Centralized logger creation and configuration
- **Structured data support**: Key-value logging with `logger.info("message", key=value)`
- **Comma handling**: Proper color highlighting for values containing commas
- **Backward compatibility**: Maintains existing log level configuration

### 🔧 **Technical Improvements**
- **Regex-based highlighting**: Custom Rich highlighter for consistent color application
- **Pattern matching**: Smart regex patterns that handle complex values with spaces and commas
- **Fallback support**: Graceful degradation to standard logging if Rich is unavailable
- **Context support**: Logger context with `logger.with_context(session_id="abc")`

### 📚 **Documentation Updates**
- **README.md**: Added structured logging section with examples
- **Tech steering**: Updated architecture notes to reflect new logging system
- **Dependencies**: Added Rich to core dependencies list

## [2.1.0] - 2025-08-14

### 🎯 **Formatting System Overhaul**
- **Unified approach**: All channels now use consistent markdown-to-HTML formatting
- **Simplified flow**: LLM outputs simple markdown (`**bold**`, `` `code` ``) → converts to clean HTML
- **Removed complexity**: Eliminated MarkdownV2 escaping and HTML fixing logic
- **Better reliability**: Clean conversion process with fewer error points

### 🎨 **Emoji-Rich Visual Structure**
- **Enhanced all prompts**: Rich emoji formatting for better visual appeal
- **Channel-specific emojis**: Tailored emoji sets for each content type
  - 🎯 📋 🔸 🔢 📊 ⚙️ 🏆 🤖 📄 (Two Minute Papers - AI research)
  - 🎯 📋 🔸 🔢 🛠️ 📊 🔄 💼 💡 ⚠️ ✅ 💻 💰 (David Ondrej - Tech tutorials)
  - 🎯 📋 🔸 🔢 🚀 📏 ⚡ ⏰ 🛠️ 💡 🏗️ 🌌 (Isaac Arthur - Space tech)
  - 🎯 📋 🔸 🔢 📊 💰 📈 ⚠️ 🪙 (RobynHD - Crypto analysis)
  - 🎯 📋 🔸 🔢 💰 🌍 📅 👤 📄 (Ivan Yakovina - Geopolitics)
- **Better scanning**: Emojis make content easier to scan and more engaging
- **Visual hierarchy**: Clear structure with emoji-coded sections

### 📝 **Updated All Channel Prompts**
- **David Ondrej**: Updated to use markdown formatting
- **Two Minute Papers**: Updated to use markdown formatting  
- **Isaac Arthur**: Updated to use markdown formatting
- **RobynHD**: Updated to use markdown formatting (German)
- **Ivan Yakovina**: Updated to use markdown formatting (Russian)
- **Example Channel**: Updated comprehensive template

### 🧹 **Code Cleanup**
- **Removed unused functions**: Eliminated `fix_malformed_html()` and `clean_markdownv2_for_telegram()`
- **Simplified validators**: Streamlined cleaning logic for markdown input
- **Updated documentation**: README reflects current markdown-to-HTML approach
- **Consistent formatting**: All prompts follow same structure and rules

### 📚 **Documentation Updates**
- **README.md**: Updated to reflect markdown-to-HTML conversion flow
- **Prompt templates**: All channels now have consistent formatting instructions
- **Clear guidelines**: Specific rules for **bold**, `code`, and structure formatting

### 🔧 **Technical Improvements**
- **Cleaner conversion**: `convert_markdown_to_clean_html()` handles **bold** → `<b>bold</b>`
- **Better escaping**: Proper HTML entity escaping while preserving formatting tags
- **Simplified telegram service**: Direct conversion without complex HTML fixing
- **Reduced error surface**: Fewer places for formatting to break

## [2.0.0] - Previous Release
- Smart message splitting with Part 1/2 format
- Comprehensive AI summaries preserving creator voices
- Advanced subtitle cleaning with 88-89% size reduction
- Multi-language support and robust error handling
- Smart channel setup with automated analysis

---

## Migration Notes

If you have custom channel prompts, update them to use the new formatting guidelines:

```markdown
**FORMAT FOR TELEGRAM (PLAIN TEXT WITH STRUCTURE):**
Use NO HTML tags at all. Instead use:
- Headers: **Bold text** (markdown style)
- Bullet points: • (bullet character)
- Code: `text` (backticks)
- Visual separators: ━━━━━━━━━━
- Emojis for structure: 🎯 📋 🔸 🔢

CRITICAL RULES:
- NO HTML tags whatsoever (<b>, <code>, etc.)
- Use **text** for emphasis instead of <b>text</b>
- Use `text` for code instead of <code>text</code>
- Keep it simple and clean
- Focus on content structure with emojis and separators
```

The system will automatically convert this to clean HTML for Telegram delivery.