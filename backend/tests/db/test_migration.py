from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_migration_creates_extensions_and_indexes(session: AsyncSession) -> None:
    extensions = set((await session.execute(text("select extname from pg_extension"))).scalars())
    assert {"vector", "pg_trgm"} <= extensions

    indexes = {
        row.indexname: row.indexdef
        for row in await session.execute(
            text("select indexname, indexdef from pg_indexes where tablename = 'chunks'")
        )
    }
    assert "hnsw" in indexes["ix_chunks_embedding_hnsw"]
    assert "vector_cosine_ops" in indexes["ix_chunks_embedding_hnsw"]
    assert "gin_trgm_ops" in indexes["ix_chunks_text_trgm"]


async def test_chunk_tsv_is_generated(session: AsyncSession) -> None:
    await session.execute(
        text(
            "insert into entities (id, kind, path, name, aliases, data, content_hash) "
            "values ('project:x', 'project', 'projects[x]', 'X', '{}', '{}', 'h')"
        )
    )
    await session.execute(
        text(
            "insert into chunks (id, entity_id, path, text, lang, content_hash, embedding) "
            "values ('projects[x].summary', 'project:x', 'projects[x].summary', 'Bazel builds', "
            "'en', 'h', :v)"
        ),
        {"v": "[" + ",".join(["0"] * 1535 + ["1"]) + "]"},
    )
    tsv = (await session.execute(text("select tsv::text from chunks"))).scalar_one()
    assert "'bazel'" in tsv
