# Gemini + RSS 自动行业简报

## 方案
- 新闻获取：Google News RSS
- 筛选、摘要与中英双语：Gemini API
- 网页：GitHub Pages
- 定时任务：GitHub Actions
- 不使用 OpenAI API，也不使用 Gemini Google Search Grounding

## 部署
1. 新建 GitHub 仓库，将压缩包内所有文件上传到仓库根目录，确保 `.github` 未遗漏。
2. 在 Google AI Studio 创建 Gemini API Key。
3. GitHub：`Settings → Secrets and variables → Actions → New repository secret`。
4. 名称填写 `GEMINI_API_KEY`，值粘贴 Gemini Key。
5. GitHub：`Settings → Pages`，选择 `Deploy from a branch`、`main`、`/(root)`。
6. 进入 `Actions → Update daily brief → Run workflow` 手动测试一次。
7. 成功后每天上海时间约 08:10 自动更新。

## 检查
- `data/briefs.json` 会写入当天简报。
- Actions 日志会显示 Gemini Token 用量。
- 页面支持 CH / EN 与日期筛选。

## 限制
RSS通常只有标题和短摘要，因此本版本会保守写作，不根据未获取到的全文补充事实。Gemini免费额度、模型可用性和速率限制以Google AI Studio实际显示为准。
