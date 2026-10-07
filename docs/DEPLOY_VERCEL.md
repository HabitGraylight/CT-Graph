# 部署在线调酒手记

[English](DEPLOY_VERCEL.en.md) · 默认界面为中文。

本项目新增了独立的多用户网页：Vercel 提供网页与 Python 调酒接口，Supabase 提供邮箱账号、PostgreSQL 数据库和按用户隔离的访问策略。没有模型 API 费用或模型密钥依赖。

本机已有的书籍、配方、库存、试饮和报告不会上传。在线数据库从空数据开始；只有用户主动发布的配方才进入社区酒单。

## 1. 创建 Supabase 项目

1. 打开 [Supabase 控制台](https://supabase.com/dashboard)，注册或登录，创建一个新项目。
2. 保存数据库密码在自己的密码管理器里。本应用不需要把这个密码放进代码或 Vercel。
3. 在项目的 **SQL Editor** 中新建查询，粘贴仓库 [cloud/schema.sql](../cloud/schema.sql) 的完整内容并执行。
4. 在 Table Editor 确认出现 `profiles`、`recipes`、`tastings` 三张表；三张表均启用 RLS。
5. 在项目的 Connect / API 设置中找到 **Project URL** 和 **Publishable key**（以 `sb_publishable_` 开头）。旧版 `anon` key 也可使用。不要选 secret key 或 service-role key。

`schema.sql` 是新项目的首次建库脚本，只运行一次。以后升级使用独立迁移，不能先删表再重跑。不要为了消除报错关闭 RLS。

## 2. 导入到 Vercel

1. 打开 [Vercel 新建项目](https://vercel.com/new)，通过 GitHub 导入 `HabitGraylight/CT-Graph`。
2. Root Directory 使用仓库根目录；Framework Preset 选择 **Other**。
3. 仓库的 `vercel.json` 已设置：

   | 设置 | 值 |
   |---|---|
   | Build Command | `python scripts/build_cloud.py` |
   | Output Directory | `cloud-dist` |
   | Python API | `api/app.py` → `/api/app` |

4. 首次可以直接 Deploy，得到 Vercel 分配的网址。未配置账号时，网站会显示“体验版”，评价和补全可用，账号及保存功能不伪装成成功。
5. 记下这个项目的稳定 Production 域名，例如 `https://your-project.vercel.app`。不要使用每次部署变化的预览地址作为正式登录地址。

推荐通过 GitHub 导入，不要把整个本机工作目录拖进部署平台。静态构建只复制 4 个公开网页文件，函数另外排除本地数据目录。

## 3. 配置三个环境变量

在 Vercel 项目 **Settings → Environment Variables** 添加以下变量，至少勾选 Production：

| 名称 | 内容 | 用途 |
|---|---|---|
| `SUPABASE_URL` | 新项目的 `https://…supabase.co` 地址 | 账号和数据库地址 |
| `SUPABASE_PUBLISHABLE_KEY` | Publishable key，或旧版 anon key | 配合用户 JWT 与 RLS 使用 |
| `APP_ORIGIN` | 正式网站的 `https://…vercel.app` 或自定义域名 | 登录跳转与同源请求检查；不要带路径或末尾 `/` |

这些变量在服务端使用。不要填写数据库密码、service-role key，不要把任何真实凭据写入 GitHub。

然后到 **Deployments → Redeploy**，让新部署读取变量。若以后换域名，要同步修改 `APP_ORIGIN`、Supabase URL 配置并重新部署。Preview 环境若未单独配置，只用于体验；不能在不匹配的预览域名上复用正式登录回调。

## 4. 配置注册、确认邮件与重置密码

在 Supabase **Authentication** 中：

1. Email provider 开启邮箱和密码登录，保留邮箱确认。
2. URL Configuration：Site URL 设置成 `APP_ORIGIN`，Redirect URLs 添加 `APP_ORIGIN/` 的实际完整地址。
3. 保留默认确认邮件及重置密码链接模板。链接完成验证后回到本站，网页会将登录凭据换成 HttpOnly Cookie，并移除 URL 中的凭据。
4. 面向其他用户开放前，在 **SMTP Settings** 配置自己的邮件发送服务。需要填写服务商提供的主机、端口、用户名、密码和发件地址；这些只填在 Supabase 后台。

**不能遗漏 SMTP：** Supabase 默认邮件服务只面向项目团队的预授权邮箱，不适合让普通访客注册。可选择任意支持 SMTP 的邮件服务，按其要求完成发件域名验证。该限制与设置入口见 [Supabase 官方邮件说明](https://supabase.com/docs/guides/auth/auth-smtp)。

不要为绕过邮件配置而关闭邮箱确认。如果收不到信，先检查 SMTP、发件域名验证、垃圾箱、邮箱限流和回调地址。

## 5. 上线后怎么用

### 普通用户

1. 点击“登录 / 注册”，填写邮箱和至少 10 位密码，完成邮箱确认。
2. 打开“我的风味”，填写昵称和六项希望的强度；不确定的项目留空。
3. 在“调配工作台”选择框架，填写原料和用量，评价或补全；勾选“参考我的风味基准”启用个人依据。
4. 给配方命名，保存为**私有版本**。修改后另存新版本，旧评分不会跟着新配方走。
5. 真实制作并试饮后，记录整体喜欢程度、六项实际强度和可选的七维质量。强度与质量不是同一个分数。
6. 若愿意分享，在“我的风味”发布配方；先检查公开预览，再确认。记录他人的公开配方时，主动勾选匿名汇总，评分才用于社区统计。

### 风味基准如何变化

- 自报偏好是初始目标，不凭空假设每个人都是 5 分。
- 最近 200 个版本中，喜欢程度 ≥7 的实际风味强度参与基准；同一版本只保留该账号最新记录。
- 有自报偏好时，采用 `(实饮强度之和 + 3 × 自报目标) / (实饮数量 + 3)`；没有自报偏好时，只用已记录强度均值。
- 可以按框架查看。制作时的个人建议只使用当前框架的实饮记录。
- 低甜感目标影响**尚未填写用量**的糖浆槽位，或提出原版与少糖浆版对照；不会悄悄修改已填写的量。
- 这是可解释的试配启发式，还不是成分到喜欢程度的预测模型。

### 高分配方如何入选

- 只有主动公开的配方版本参与。
- 至少 3 位非作者账号自报按版本实际制作并试饮，且同意贡献评分。
- 每个账号每个版本一票；再次记录更新旧票，不叠加。
- 平均喜欢程度 ≥7 才标记“高分入选”。排序使用固定先验收缩分：`(评分总和 + 5×6) / (人数 + 5)`，同时展示原始均分和人数。
- 不足 3 人不公开均分；每个风味维度也分别满足 3 人后才显示平均强度。
- 作者自评分不参与榜单；撤回公开或撤销评分汇总同意会退出相关统计。私人文字笔记始终不公开。

个人列表和导出展示最近 50 个配方版本与 200 条试饮；社区最多显示排序靠前的 100 个公开版本。界面人数与版本数是当前窗口内的数量，尚未提供全量分页。

目前是小规模社区版本，尚无真人去重、反刷榜、举报审核后台。多账号可能影响排序；不要把排名当成客观质量认证。大规模开放前再增加这些能力。

## 6. 配置后的验收

用两个不同邮箱和两个浏览器会话检查：

- A 注册并验证邮箱；创建私有配方；B 看不到它。
- A 发布后，B 可见配方并记录自己的实饮；B 仍看不到 A 的笔记和风味问卷。
- A 撤回后，该版本从社区消失。
- B 修改自己对同一版本的评分，不增加票数。
- 测试退出、重新登录、忘记密码、邮件链接回到正式域名。

不要为了测试榜单给真实社区编造试饮。仓库已有纯合成的数据库测试覆盖门槛和排序。

## 本地开发与自动验证

```powershell
python scripts/cloud_preview.py --port 8877
python -m unittest discover -s tests -q
node --check cloud/web/app.js
python scripts/build_cloud.py
npm ci --prefix tests/database --ignore-scripts
npm test --prefix tests/database
npm ci --prefix tests/web --ignore-scripts
npm test --prefix tests/web
```

预览地址 `http://127.0.0.1:8877/`。没有环境变量也能体验公开引擎。如果要本地测试真实账号，用独立测试 Supabase 项目，将 `APP_ORIGIN` 设为此地址并加入测试项目允许的回调。不要在公开 Preview 环境连接正式用户库。

数据库测试通过 PGlite 执行实际 PostgreSQL 的建表、约束、RLS 和触发器，使用虚构账号；不验证 Supabase 的真实邮件投递。Python 测试还验证云端不会读取本地数据，以及会话 Cookie 和来源校验。前端测试在隔离 DOM 中验证交互逻辑，不代表浏览器视觉验收。

本次交付没有创建你的 Vercel/Supabase 项目，也没有发送真实注册邮件。完成以上配置后再执行线上验收。

参考：[Vercel Python API 路由](https://vercel.com/docs/functions/runtimes/python/api-directory)、[Vercel Git 部署](https://vercel.com/docs/git)、[Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)、[Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)。
