# GitHub Pages 固定網址部署

這個方案會把網站部署到固定網址：

`https://<你的 GitHub 帳號>.github.io/<repo 名稱>/`

## 建議設定

1. 建立一個 GitHub repo，例如 `worldcup-odds-warroom-2026`。
2. 把這個資料夾推到 repo 的 `main` branch。
3. 到 repo 的 `Settings > Pages`，把 Source 設成 `GitHub Actions`。
4. 到 `Settings > Secrets and variables > Actions` 新增兩個 secret：
   - `BINANCE_API_KEY`
   - `BINANCE_API_SECRET`
5. 到 `Actions` 手動執行 `Deploy World Cup dashboard` 一次。

## 更新規則

- 平常每 30 分鐘更新一次。
- 已知賽中時段會每 5 分鐘更新一次。
- 每次 workflow 會更新 ESPN / 台灣運彩 / Binance 盤口，重建 `site-canada-morocco/public/index.html`，並部署到 GitHub Pages。
- 更新後會把狀態檔和輸出資料 commit 回 repo，避免每次排程都從舊狀態重跑。

## 注意

- GitHub Actions 的 cron 不是即時系統，可能延遲幾分鐘。
- Binance 憑證不能 commit 到 repo，只能放 GitHub Secrets。
- 如果 repo 是 private，請確認你的 GitHub 帳號方案允許 GitHub Pages。
