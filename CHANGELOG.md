# Changelog

## [2.4.0] - 2025-10-07

### 💰 **Cost Tracking & Model Updates**
- **Real cost tracking**: Actual costs from OpenRouter API responses stored in database
- **Cost extraction**: Multi-location checking for OpenRouter cost data (usage.cost, x_openrouter.cost, headers)
- **Cost aggregation**: Total costs calculated from all 3 API calls (primary + secondary + synthesis)
- **Database storage**: `cost_estimate` field stores actual USD costs, `token_usage_json` stores detailed breakdown
- **Analytics ready**: Cost data structured for GUI analytics dashboard

### 🤖 **Model Configuration Updates**
- **New primary model**: `z-ai/glm-4.6` (Zhipu AI's fast GLM model)
- **New secondary model**: `anthropic/claude-3.5-haiku` (latest Claude Haiku)
- **New synthesis model**: `mistralai/mistral-medium-3.1` (Mistral's medium-tier model)
- **Diverse AI providers**: Three different providers (Zhipu, Anthropic, Mistral) for enhanced quality
- **All channels updated**: 7 channel configs + .env file updated with new models

### ⚙️ **Configuration Simplification**
- **Removed cost thresholds**: No automatic fallback based on content length (50,000 char threshold removed)
- **Boolean toggle**: Multi-model is now simple `enabled: true/false` setting
- **Explicit control**: Users choose single vs multi-model mode directly
- **No token estimation**: Removed complex token counting and threshold logic
- **Cleaner configs**: Simplified YAML configuration files

### 🐛 **Bug Fixes**
- **Anton Petrov channel**: Fixed failed summarizations caused by old free model references
- **Database cleanup**: Removed failed videos to allow reprocessing
- **Model references**: Updated all hardcoded model references to new selections

### 📚 **Documentation Updates**
- **README updated**: New model configuration examples and cost tracking info
- **COST_TRACKING_IMPLEMENTATION.md**: Detailed implementation documentation
- **MODEL_UPDATE_SUMMARY.md**: Complete model change summary
- **Configuration examples**: Updated with latest model selections

## [2.3.0] - 2025-02-09

### 🤖 **Multi-Model Summarization System**
- **Dual-model approach**: Enhanced quality through intelligent synthesis of multiple AI models
- **Model flexibility**: Support for OpenAI, Anthropic, and other providers simultaneously
- **Quality synthesis**: Combines strengths of different models for optimal results
- **Configurable pipelines**: Easy setup for single-model or multi-model processing
- **Comprehensive testing**: Full test suite for multi-model functionality

### 💬 **Interactive QnA System with RAG**
- **Channel-specific conversations**: Individual knowledge bases for each monitored channel
- **Video tagging system**: Tag specific videos for targeted questioning with full context
- **Semantic search**: Find relevant content across all videos in a channel
- **Context-aware responses**: Answers based on actual video content and summaries
- **RAG integration**: Retrieval-augmented generation for accurate, contextual responses

### 🗄️ **Enhanced Database Architecture**
- **Multi-model support**: Database schema updated for dual-model results storage
- **QnA integration**: Conversation history and video tagging support
- **Performance optimizations**: Improved query performance and indexing
- **Migration system**: Automatic database schema updates
- **Analytics support**: Enhanced metrics and reporting capabilities

### 🧪 **Comprehensive Testing Framework**
- **Multi-model testing**: Full test coverage for dual-model summarization
- **Database testing**: Comprehensive database service testing
- **Integration testing**: End-to-end testing for complete workflows
- **Performance testing**: Database performance and optimization testing
- **Error scenario testing**: Robust error handling validation

### 🏗️ **Architecture Improvements**
- **Service separation**: Clear separation between single and multi-model services
- **Configuration flexibility**: Support for both single and multi-model channel configs
- **Template system**: Synthesis template system for multi-model results
- **Error handling**: Enhanced error handling across all services
- **Code organization**: Improved project structure and maintainability

### 📚 **Documentation Enhancements**
- **Multi-model setup**: Complete guide for configuring dual-model processing
- **QnA system usage**: Documentation for interactive bot functionality
- **Architecture docs**: Updated system architecture documentation
- **Configuration examples**: Comprehensive configuration examples
- **Migration guides**: Clear upgrade paths for existing installations

### 🔧 **Technical Improvements**
- **Synthesis templates**: Intelligent combination of multiple model outputs
- **Configuration validation**: Enhanced validation for multi-model setups
- **Performance monitoring**: Better metrics and monitoring capabilities
- **Resource optimization**: Improved resource usage and efficiency
- **Backward compatibility**: Full compatibility with existing single-model setups

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