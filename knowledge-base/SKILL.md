---
name: local-knowledge-base
description: '本地知识库向量搜索技能。基于 TF-IDF + 余弦相似度实现文档向量化索引和语义检索，纯离线运行，无需下载外部模型。支持 Markdown、TXT、PDF 文档的自动分块、向量化、增量索引和语义搜索。Trigger phrases: 知识库搜索, 查知识库, 搜索文档, 语义搜索, 向量搜索, 全文检索, 查找资料, 文档检索, vector-db, knowledge base, 索引文档, 向量化, 搜知识库, 查文档.'
description_zh: 本地知识库向量搜索（TF-IDF 向量化索引与语义检索，纯离线）
description_en: Local knowledge base vector search with TF-IDF indexing and semantic retrieval, fully offline
version: 2.0.0
metadata:
  clawdbot:
    requires:
      env: []
    primaryEnv: ""
---

# 本地知识库向量搜索技能 v2

基于 TF-IDF + 余弦相似度的本地知识库，支持文档向量化索引和语义检索。**纯离线运行，无需下载外部模型。**

## 能力总览

| 能力 | 说明 | 命令 |
|------|------|------|
| **构建索引** | 扫描目录，分块向量化，构建 TF-IDF 索引 | `index` |
| **增量索引** | 只处理新增/修改的文件 | `index`（不加 --force） |
| **语义搜索** | 自然语言查询，返回最相关的文档片段 | `search` |
| **查看状态** | 查看当前索引的文档块数和配置 | `status` |

## 首次使用 — 环境检查

### 步骤 1：检查 Python 依赖

```bash
py -c "import sklearn; import numpy; print('OK')"
```

如果失败，安装依赖：

```bash
py -m pip install scikit-learn numpy --quiet
```

### 步骤 2（可选）：PDF 支持

如需索引 PDF 文件，安装 PyMuPDF：

```bash
py -m pip install pymupdf --quiet
```

## 使用方法

### 1. 构建索引

```bash
py {baseDir}/scripts/kb_indexer.py index --source "<知识库文档目录>"
```

| 参数 | 必需 | 说明 |
|------|:---:|------|
| `--source` | ✅ | 文档目录路径 |
| `--db` | ❌ | 索引存储目录（默认 `{baseDir}/db`） |
| `--chunk-size` | ❌ | 分块大小字符数（默认 500） |
| `--overlap` | ❌ | 分块重叠字符数（默认 50） |
| `--force` | ❌ | 强制重建全部索引 |

**示例**：

```bash
# 首次索引
py {baseDir}/scripts/kb_indexer.py index --source "D:\天翼云等保知识库"

# 增量更新（只处理新增/修改的文件）
py {baseDir}/scripts/kb_indexer.py index --source "D:\天翼云等保知识库"

# 强制全量重建
py {baseDir}/scripts/kb_indexer.py index --source "D:\天翼云等保知识库" --force
```

### 2. 语义搜索

```bash
py {baseDir}/scripts/kb_indexer.py search "三级等保安全物理环境要求"
```

| 参数 | 必需 | 说明 |
|------|:---:|------|
| `query` | ✅ | 搜索查询文本 |
| `--db` | ❌ | 索引存储目录（默认 `{baseDir}/db`） |
| `--top-k` | ❌ | 返回结果数（默认 5） |

### 3. 查看索引状态

```bash
py {baseDir}/scripts/kb_indexer.py status
```

## 支持的文件格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| Markdown | `.md` | 原生支持 |
| 纯文本 | `.txt` | 原生支持 |
| PDF | `.pdf` | 需安装 PyMuPDF |

## 技术细节

- **向量化方法**: TF-IDF（词频-逆文档频率）
- **分词策略**: 中文单字 + bigram + 英文单词
- **相似度计算**: 余弦相似度（cosine similarity）
- **索引存储**: 本地文件（pickle + npz），数据不出本机
- **增量索引**: 基于 MD5 哈希判断文件是否修改
- **隐私安全**: 纯离线运行，不发送任何数据到外部服务
- **依赖**: scikit-learn, numpy（均为纯 Python/离线可用）

## 常见问题

**Q: 首次索引很慢？**
A: TF-IDF 方案无需下载模型，首次索引速度取决于文档数量。数百份文档通常在几秒内完成。

**Q: 如何添加新文档？**
A: 将文档放入知识库目录，重新运行 index 命令（不加 --force），只处理新增/修改的文件。

**Q: 搜索结果不准？**
A: 尝试调整 --chunk-size（增大可保留更多上下文）或 --top-k（返回更多结果）。中文搜索效果受分词策略影响，可优化 `chinese_tokenizer` 函数。

**Q: 与深度学习嵌入模型（如 text2vec）的区别？**
A: TF-IDF 基于词频统计，对精确关键词匹配效果好；深度学习模型对语义理解更好但需要下载大模型（400MB+）和网络连接。本方案优先保证离线可用。
