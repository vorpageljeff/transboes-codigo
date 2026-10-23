from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.models.freight import FreightValidationStatus


@dataclass(frozen=True)
class FreightValidationResult:
    received_amount: Decimal
    expected_amount: Decimal | None
    difference: Decimal | None
    status: FreightValidationStatus
    explanation: str


class FreightValidationEngine(Protocol):
    def validate(
        self, received_amount: Decimal, expected_amount: Decimal | None = None
    ) -> FreightValidationResult: ...


class ConfigurableFreightValidationEngine:
    def __init__(self, mode: str):
        self.mode = mode

    def validate(
        self, received_amount: Decimal, expected_amount: Decimal | None = None
    ) -> FreightValidationResult:
        if self.mode == "PASS_THROUGH":
            return FreightValidationResult(
                received_amount,
                received_amount,
                Decimal(0),
                FreightValidationStatus.OK,
                "Modo PASS_THROUGH: o valor recebido foi aceito sem fórmula externa.",
            )
        if self.mode == "MANUAL" and expected_amount is not None:
            difference = received_amount - expected_amount
            status = (
                FreightValidationStatus.OK if difference == 0 else FreightValidationStatus.DIVERGENT
            )
            return FreightValidationResult(
                received_amount,
                expected_amount,
                difference,
                status,
                "Valor esperado informado manualmente por usuário autorizado.",
            )
        return FreightValidationResult(
            received_amount,
            None,
            None,
            FreightValidationStatus.WAITING_RULE,
            "Regra oficial de frete ainda não cadastrada; nenhuma fórmula foi presumida.",
        )
