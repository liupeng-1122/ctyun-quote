#!/usr/bin/env python3
"""
本地知识库向量化索引工具 v2
- 基于 TF-IDF + 余弦相似度，纯离线运行，无需下载外部模型
- 支持 Markdown、TXT、PDF 文档的自动分块、索引和语义搜索
- 支持增量索引（只处理新增/修改的文件）

用法:
  py kb_indexer.py index    --source <文档目录> [--db <索引目录>] [--chunk-size 500] [--overlap 50] [--force]
  py kb_indexer.py search   "查询内容" [--db <索引目录>] [--top-k 5]
  py kb_indexer.py status   [--db <索引目录>]
  py kb_indexer.py maintain [--source <文档目录>] [--db <索引目录>]
"""

import argparse
import hashlib
import json
import os
import pickle
import re
import sys
import math
from collections import Counter
from pathlib import Path

# PDF 支持
try:
    import fitz  # PyMuPDF
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

# scikit-learn（离线可用）
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {".md", ".txt"}
if HAS_PDF:
    SUPPORTED_EXTENSIONS.add(".pdf")

# 默认索引目录
DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db")


def get_file_hash(filepath: str) -> str:
    """计算文件的 MD5 哈希值"""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_file_content(filepath: str) -> str:
    """读取文件内容，支持 txt/md/pdf"""
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        if not HAS_PDF:
            return ""
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    else:
        for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                with open(filepath, "r", encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        return ""


def chinese_tokenizer(text: str) -> list:
    """简单的中文分词器：按字符 bigram + 单字 + 英文单词切分"""
    tokens = []
    # 提取英文单词
    eng_words = re.findall(r'[a-zA-Z][a-zA-Z0-9]*', text.lower())
    tokens.extend(eng_words)
    # 提取中文字符（单字）
    cn_chars = re.findall(r'[\u4e00-\u9fff]', text)
    tokens.extend(cn_chars)
    # 中文字符 bigram
    for i in range(len(cn_chars) - 1):
        tokens.append(cn_chars[i] + cn_chars[i + 1])
    return tokens


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """将长文本按字符数分块，支持重叠"""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def scan_documents(source_dir: str) -> list:
    """扫描目录，返回所有支持格式的文件信息"""
    documents = []
    source_path = Path(source_dir)
    if not source_path.exists():
        print(f"错误: 目录不存在 - {source_dir}")
        return documents
    for filepath in source_path.rglob("*"):
        if filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
            parts = filepath.relative_to(source_path).parts
            if any(p.startswith(".") for p in parts):
                continue
            if any(p in {"node_modules", "__pycache__", ".git", ".workbuddy"} for p in parts):
                continue
            file_hash = get_file_hash(str(filepath))
            documents.append({
                "path": str(filepath),
                "relative_path": str(filepath.relative_to(source_path)),
                "filename": filepath.name,
                "extension": filepath.suffix.lower(),
                "hash": file_hash,
                "size": filepath.stat().st_size,
            })
    return documents


def build_index(
    source_dir: str,
    db_dir: str,
    chunk_size: int = 500,
    overlap: int = 50,
    force: bool = False,
):
    """构建/更新 TF-IDF 向量索引"""
    print("=" * 60)
    print("本地知识库向量化索引工具 v2")
    print("=" * 60)
    print(f"文档目录: {source_dir}")
    print(f"索引目录: {db_dir}")
    print(f"分块大小: {chunk_size} 字符, 重叠: {overlap} 字符")
    print(f"强制重建: {'是' if force else '否'}")
    print()

    if not HAS_SKLEARN:
        print("错误: 请先安装依赖: py -m pip install scikit-learn numpy")
        return

    # 1. 扫描文档
    print("[1/4] 扫描文档...")
    documents = scan_documents(source_dir)
    print(f"  找到 {len(documents)} 个文档文件")
    if not documents:
        print("  未找到文档，请确认目录和文件格式。")
        return

    # 2. 读取已有索引元数据
    print("[2/4] 检查增量索引...")
    os.makedirs(db_dir, exist_ok=True)
    meta_path = os.path.join(db_dir, "meta.json")
    file_hashes = {}
    if os.path.exists(meta_path) and not force:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            file_hashes = meta.get("file_hashes", {})
        print(f"  已有索引记录 {len(file_hashes)} 个文件")
    else:
        print("  首次索引或强制重建")

    # 3. 读取文件内容并分块
    print("[3/4] 读取文档并分块...")
    all_chunks = []
    skipped = 0
    for doc in documents:
        if not force and doc["relative_path"] in file_hashes:
            if file_hashes[doc["relative_path"]] == doc["hash"]:
                skipped += 1
                continue
        content = read_file_content(doc["path"])
        if not content.strip():
            continue
        chunks = chunk_text(content, chunk_size, overlap)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id": f"{doc['relative_path']}__chunk_{i}",
                "text": chunk,
                "metadata": {
                    "relative_path": doc["relative_path"],
                    "filename": doc["filename"],
                    "extension": doc["extension"],
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "file_hash": doc["hash"],
                    "file_size": doc["size"],
                }
            })
    if skipped > 0:
        print(f"  跳过 {skipped} 个未修改的文件（增量索引）")
    if not all_chunks:
        print("  没有新增或修改的文档需要索引。")
        return
    print(f"  生成 {len(all_chunks)} 个文本块")

    # 4. 向量化并存储
    print("[4/4] 构建向量索引...")
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    # 加载已有数据（增量合并）
    existing_texts = []
    existing_metas = []
    chunks_path = os.path.join(db_dir, "chunks.pkl")
    if os.path.exists(chunks_path) and not force:
        with open(chunks_path, "rb") as f:
            old_data = pickle.load(f)
            old_texts = old_data.get("texts", [])
            old_metas = old_data.get("metadatas", [])
            # 过滤掉被更新的文件的旧块
            updated_files = set(m["relative_path"] for m in metadatas)
            for t, m in zip(old_texts, old_metas):
                if m["relative_path"] not in updated_files:
                    existing_texts.append(t)
                    existing_metas.append(m)

    # 合并
    all_texts = existing_texts + texts
    all_metas = existing_metas + metadatas

    # 构建 TF-IDF 向量
    vectorizer = TfidfVectorizer(
        tokenizer=chinese_tokenizer,
        token_pattern=None,  # 禁用默认 token_pattern
        lowercase=True,
        max_features=50000,
        min_df=1,
        max_df=0.95,
    )
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    print(f"  TF-IDF 矩阵: {tfidf_matrix.shape[0]} 个文档 × {tfidf_matrix.shape[1]} 个特征")

    # 保存索引数据
    with open(chunks_path, "wb") as f:
        pickle.dump({"texts": all_texts, "metadatas": all_metas}, f)

    with open(os.path.join(db_dir, "vectorizer.pkl"), "wb") as f:
        pickle.dump(vectorizer, f)

    import scipy.sparse
    scipy.sparse.save_npz(os.path.join(db_dir, "tfidf_matrix.npz"), tfidf_matrix)

    # 保存元数据
    new_file_hashes = {m["relative_path"]: m["file_hash"] for m in all_metas}
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "file_hashes": new_file_hashes,
            "total_chunks": len(all_texts),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "source_dir": os.path.abspath(source_dir),
        }, f, ensure_ascii=False, indent=2)

    print()
    print("[OK] 索引完成!")
    print(f"  处理文档数: {len(documents)}")
    print(f"  新增/更新块数: {len(texts)}")
    print(f"  数据库总块数: {len(all_texts)}")
    print(f"  索引路径: {db_dir}")


def search(query: str, db_dir: str, top_k: int = 5):
    """语义搜索知识库"""
    if not HAS_SKLEARN:
        print("错误: 请先安装依赖: py -m pip install scikit-learn numpy")
        return None

    chunks_path = os.path.join(db_dir, "chunks.pkl")
    vectorizer_path = os.path.join(db_dir, "vectorizer.pkl")
    matrix_path = os.path.join(db_dir, "tfidf_matrix.npz")

    for p in [chunks_path, vectorizer_path, matrix_path]:
        if not os.path.exists(p):
            print(f"错误: 索引文件不存在 ({p})，请先运行 index 命令")
            return None

    # 加载索引数据
    with open(chunks_path, "rb") as f:
        data = pickle.load(f)
    texts = data["texts"]
    metas = data["metadatas"]

    with open(vectorizer_path, "rb") as f:
        vectorizer = pickle.load(f)

    import scipy.sparse
    tfidf_matrix = scipy.sparse.load_npz(matrix_path)

    # 查询向量化
    query_vec = vectorizer.transform([query])
    # 计算余弦相似度
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    # 取 top-k
    top_indices = scores.argsort()[-top_k:][::-1]

    results = {
        "query": query,
        "total": len(texts),
        "results": [],
    }
    for idx in top_indices:
        if scores[idx] < 0.01:  # 过滤极低分
            continue
        results["results"].append({
            "score": float(scores[idx]),
            "text": texts[idx],
            "metadata": metas[idx],
        })
    return results


def maintain(db_dir: str, source_dir: str = None):
    """维护知识库：清理冗余索引、去重、压缩、校验完整性"""
    print("=" * 60)
    print("本地知识库维护工具")
    print("=" * 60)
    print(f"索引目录: {db_dir}")
    print()

    meta_path = os.path.join(db_dir, "meta.json")
    chunks_path = os.path.join(db_dir, "chunks.pkl")
    vectorizer_path = os.path.join(db_dir, "vectorizer.pkl")
    matrix_path = os.path.join(db_dir, "tfidf_matrix.npz")

    # 检查索引是否存在
    if not os.path.exists(meta_path):
        print("错误: 索引不存在，请先运行 index 命令")
        return

    # 加载数据
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    with open(chunks_path, "rb") as f:
        data = pickle.load(f)
    texts = data["texts"]
    metas = data["metadatas"]

    original_count = len(texts)
    print(f"[1/5] 当前索引状态: {original_count} 个文本块, {len(meta.get('file_hashes', {}))} 个文件")

    # ---- 步骤 2: 清理源文件已删除的孤立块 ----
    print("[2/5] 清理孤立块（源文件已删除的块）...")
    if source_dir and os.path.exists(source_dir):
        # 扫描当前存在的文件
        current_docs = scan_documents(source_dir)
        current_files = set(d["relative_path"] for d in current_docs)
        # 检查索引中的文件是否还存在
        indexed_files = set(m["relative_path"] for m in metas)
        orphan_files = indexed_files - current_files
        if orphan_files:
            new_texts = []
            new_metas = []
            removed_chunks = 0
            for t, m in zip(texts, metas):
                if m["relative_path"] in orphan_files:
                    removed_chunks += 1
                else:
                    new_texts.append(t)
                    new_metas.append(m)
            texts = new_texts
            metas = new_metas
            print(f"  清理 {len(orphan_files)} 个已删除文件的 {removed_chunks} 个孤立块")
            # 更新 file_hashes
            for f in orphan_files:
                meta["file_hashes"].pop(f, None)
        else:
            print("  无孤立块")
    else:
        print("  跳过（未提供源目录或目录不存在）")

    # ---- 步骤 3: 去重（内容完全相同的块） ----
    print("[3/5] 去重（内容完全相同的文本块）...")
    seen = {}
    unique_texts = []
    unique_metas = []
    duplicates = 0
    for t, m in zip(texts, metas):
        # 用文本前100字符+文件路径+块索引作为去重键
        dedup_key = (t[:100], m["relative_path"], m["chunk_index"])
        if dedup_key in seen:
            duplicates += 1
        else:
            seen[dedup_key] = True
            unique_texts.append(t)
            unique_metas.append(m)
    texts = unique_texts
    metas = unique_metas
    if duplicates > 0:
        print(f"  去除 {duplicates} 个重复块")
    else:
        print("  无重复块")

    # ---- 步骤 4: 索引完整性校验 ----
    print("[4/5] 校验索引完整性...")
    errors = []
    # 检查块数量一致性
    if len(texts) != len(metas):
        errors.append(f"文本块数({len(texts)})与元数据数({len(metas)})不一致")
    # 检查每个文件的块索引连续性
    file_chunks = {}
    for m in metas:
        rp = m["relative_path"]
        if rp not in file_chunks:
            file_chunks[rp] = []
        file_chunks[rp].append(m["chunk_index"])
    for rp, chunks in file_chunks.items():
        expected = set(range(max(chunks) + 1))
        actual = set(chunks)
        if actual != expected:
            missing = expected - actual
            if missing:
                errors.append(f"{rp}: 缺少块索引 {sorted(missing)[:5]}...")
    # 检查索引文件完整性
    for p, name in [(chunks_path, "chunks.pkl"), (vectorizer_path, "vectorizer.pkl"), (matrix_path, "tfidf_matrix.npz")]:
        if not os.path.exists(p):
            errors.append(f"索引文件缺失: {name}")
    if errors:
        print(f"  发现 {len(errors)} 个问题:")
        for e in errors:
            print(f"    - {e}")
    else:
        print("  索引完整性校验通过")

    # ---- 步骤 5: 重建向量索引（压缩优化） ----
    cleaned_count = len(texts)
    if cleaned_count < original_count:
        print(f"[5/5] 重建向量索引（{original_count} -> {cleaned_count} 块）...")
        if HAS_SKLEARN and cleaned_count > 0:
            vectorizer = TfidfVectorizer(
                tokenizer=chinese_tokenizer,
                token_pattern=None,
                lowercase=True,
                max_features=50000,
                min_df=1,
                max_df=0.95,
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            print(f"  新 TF-IDF 矩阵: {tfidf_matrix.shape[0]} x {tfidf_matrix.shape[1]}")

            # 保存优化后的数据
            with open(chunks_path, "wb") as f:
                pickle.dump({"texts": texts, "metadatas": metas}, f)
            with open(vectorizer_path, "wb") as f:
                pickle.dump(vectorizer, f)
            import scipy.sparse
            scipy.sparse.save_npz(matrix_path, tfidf_matrix)

            # 更新元数据
            new_file_hashes = {m["relative_path"]: m["file_hash"] for m in metas}
            meta["file_hashes"] = new_file_hashes
            meta["total_chunks"] = cleaned_count
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            # 计算节省空间
            old_size = sum(os.path.getsize(p) for p in [chunks_path, vectorizer_path, matrix_path, meta_path] if os.path.exists(p))
            print(f"  索引文件总大小: {old_size / 1024 / 1024:.1f} MB")
        else:
            print("  跳过（无可清理内容或依赖缺失）")
    else:
        print(f"[5/5] 无需重建（块数未变化: {cleaned_count}）")

    # 汇总
    print()
    print("[OK] 维护完成!")
    print(f"  原始块数: {original_count}")
    print(f"  清理后块数: {cleaned_count}")
    print(f"  减少: {original_count - cleaned_count} 块 ({(original_count - cleaned_count) / max(original_count, 1):.1%})")
    if errors:
        print(f"  待修复问题: {len(errors)} 个")


def show_status(db_dir: str):
    """查看索引状态"""
    meta_path = os.path.join(db_dir, "meta.json")
    if not os.path.exists(meta_path):
        print(f"索引目录: {db_dir}")
        print("状态: 未建立索引")
        return
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print(f"索引目录: {db_dir}")
    print(f"源目录: {meta.get('source_dir', 'N/A')}")
    print(f"索引文档块数: {meta.get('total_chunks', 0)}")
    print(f"已索引文件数: {len(meta.get('file_hashes', {}))}")
    print(f"分块大小: {meta.get('chunk_size', 500)} 字符")
    print(f"分块重叠: {meta.get('overlap', 50)} 字符")


def main():
    parser = argparse.ArgumentParser(description="本地知识库向量化索引工具 v2")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # index 命令
    idx_p = subparsers.add_parser("index", help="构建/更新索引")
    idx_p.add_argument("--source", required=True, help="文档目录")
    idx_p.add_argument("--db", default=DEFAULT_DB_DIR, help=f"索引存储目录（默认 {DEFAULT_DB_DIR}）")
    idx_p.add_argument("--chunk-size", type=int, default=500, help="分块大小（字符数）")
    idx_p.add_argument("--overlap", type=int, default=50, help="分块重叠（字符数）")
    idx_p.add_argument("--force", action="store_true", help="强制重建索引")

    # search 命令
    s_p = subparsers.add_parser("search", help="语义搜索")
    s_p.add_argument("query", help="搜索查询")
    s_p.add_argument("--db", default=DEFAULT_DB_DIR, help="索引存储目录")
    s_p.add_argument("--top-k", type=int, default=5, help="返回结果数")

    # status 命令
    st_p = subparsers.add_parser("status", help="查看索引状态")
    st_p.add_argument("--db", default=DEFAULT_DB_DIR, help="索引存储目录")

    # maintain 命令
    mt_p = subparsers.add_parser("maintain", help="维护知识库（清理冗余、去重、压缩、校验）")
    mt_p.add_argument("--source", help="文档源目录（用于检测已删除的孤立块）")
    mt_p.add_argument("--db", default=DEFAULT_DB_DIR, help=f"索引存储目录（默认 {DEFAULT_DB_DIR}）")

    args = parser.parse_args()

    if args.command == "index":
        build_index(
            source_dir=args.source,
            db_dir=args.db,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            force=args.force,
        )
    elif args.command == "search":
        results = search(query=args.query, db_dir=args.db, top_k=args.top_k)
        if results and results["results"]:
            print(f'\n搜索: "{args.query}"')
            print(f"从 {results['total']} 个文档块中找到 {len(results['results'])} 个结果:\n")
            for i, r in enumerate(results["results"]):
                print(f"--- 结果 {i+1} (相似度: {r['score']:.2%}) ---")
                print(f"文件: {r['metadata'].get('relative_path', 'N/A')}")
                print(f"块: {r['metadata'].get('chunk_index', 0)}/{r['metadata'].get('total_chunks', '?')}")
                preview = r['text'][:200].replace('\n', ' ')
                # 替换 GBK 不兼容的特殊字符，避免 Windows 控制台编码错误
                preview = preview.replace('\u2022', '-').replace('\u2023', '-').replace('\u25cf', '*').replace('\u25cb', 'o').replace('\u2014', '--').replace('\u2013', '-').replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'").replace('\u00b7', '.')
                print(f"内容预览: {preview}...")
                print()
        else:
            print("未找到相关结果。")
    elif args.command == "status":
        show_status(args.db)
    elif args.command == "maintain":
        maintain(db_dir=args.db, source_dir=getattr(args, "source", None))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
