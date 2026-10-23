from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.api.v1.dependencies import CurrentUser, Database, require_roles
from app.models.imports import ImportRow, ImportRun
from app.models.user import User, UserRole
from app.modules.imports.service import DuplicateImportError, import_copagril_report
from app.schemas.imports import ImportRunResponse

router = APIRouter()
ImportManager = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER))]


@router.get("/imports", response_model=list[ImportRunResponse], tags=["imports"])
def list_imports(_: CurrentUser, db: Database) -> list[ImportRun]:
    return list(db.scalars(select(ImportRun).order_by(ImportRun.created_at.desc())))


@router.get("/imports/{run_id}", tags=["imports"])
def import_detail(run_id: UUID, _: CurrentUser, db: Database):
    run = db.get(ImportRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    rows = list(db.scalars(select(ImportRow).where(ImportRow.import_run_id == run.id).order_by(ImportRow.row_number)))
    return {"id": run.id, "filename": run.filename, "status": run.status, "total_rows": run.total_rows, "imported_rows": run.imported_rows, "duplicate_rows": run.duplicate_rows, "error_rows": run.error_rows, "summary": run.summary, "created_at": run.created_at, "rows": [{"row_number": row.row_number, "external_id": row.external_id, "status": row.status, "errors": row.errors, "style_markers": row.style_markers} for row in rows]}


@router.post(
    "/imports/copagril-report", response_model=ImportRunResponse, status_code=201, tags=["imports"]
)
async def upload_copagril_report(
    user: ImportManager,
    db: Database,
    file: Annotated[UploadFile, File(description="Relatório Copagril em HTML com extensão .xls")],
) -> ImportRun:
    content = await file.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="Arquivo vazio ou acima de 10 MB")
    try:
        return await run_in_threadpool(import_copagril_report,
            db, content=content, filename=file.filename or "relatorio.xls", user=user
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito de importação; revise os dados ou atualize o histórico") from exc
    except DuplicateImportError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Arquivo já importado na execução {exc.run.id}",
        ) from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="O arquivo não está em UTF-8") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
