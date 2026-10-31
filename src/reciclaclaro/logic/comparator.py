"""Evaluar hechos confirmados contra reglas, sin interpretar texto libre."""

from reciclaclaro.contracts import (
    AppError, Center, CenterRule, ComparisonResult, ConfirmedItem, Material,
    PendingQuestion, ReciclaClaroError, RuleReference,
)

_QUESTIONS = {
    "material": "Que material puedes confirmar para este objeto?",
    "presentation": "Es una botella, envase, espejo, caja u otra presentacion?",
    "resin_code": "Que numero aparece en el simbolo del plastico?",
    "color": "Que color tiene el objeto?",
    "clean": "El objeto esta limpio?",
    "residue_free": "Esta libre de restos de comida u otros residuos?",
    "corrugated": "Confirmas que es carton corrugado?",
    "wet": "El carton esta mojado?",
    "greasy": "El carton tiene grasa?",
    "painted": "El carton esta pintado?",
    "boxed": "Los envases de vidrio estan dentro de una caja?",
    "sorted_by_color": "Esta separado por los colores indicados en la regla?",
}
_BOOL_ATTRIBUTES = {
    "clean", "residue_free", "corrugated", "wet", "greasy", "painted", "boxed", "sorted_by_color",
}
_RESIN = {Material.PET_1: 1, Material.HDPE_2: 2, Material.PP_5: 5}


def _fact(item, name):
    attribute = item.attributes.get(name)
    if attribute is None or attribute.source != "user_confirmed":
        return None
    value = attribute.value
    if name in _BOOL_ATTRIBUTES and type(value) is not bool:
        return None
    if name == "resin_code" and (type(value) is not int or value not in range(1, 8)):
        return None
    if name in {"material", "presentation", "color"} and (
        not isinstance(value, str) or not value.strip() or value == "desconocido"
    ):
        return None
    return value


def _questions(names):
    return [PendingQuestion(attribute=name, question=_QUESTIONS[name]) for name in sorted(set(names))]


def _matches(item, rule):
    missing = []
    if rule.presentation is not None and item.presentation != rule.presentation:
        return False, []
    for name, expected in rule.conditions.items():
        actual = _fact(item, name)
        if actual is None:
            missing.append(name)
        elif type(actual) is not type(expected) or actual != expected:
            return False, []
    for name in rule.required_attributes:
        if _fact(item, name) is None:
            missing.append(name)
    return True, missing


def _result(item, center, acceptance, reason, rules=(), **kwargs):
    references = [RuleReference(rule_id=r.rule_id, sources=r.references)
                  for r in rules if r.rule_id and r.references]
    primary = next(iter(rules), None)
    return ComparisonResult(
        item_id=item.item_id, center_id=center.center_id, analysis_id=item.analysis_id,
        revision=item.revision, acceptance=acceptance, reason=reason,
        rule_source_url=primary.source_url if primary else None,
        consulted_on=primary.consulted_on if primary else None,
        rule_references=references, **kwargs,
    )


def _has_evidence(rule):
    return bool(rule.rule_id and rule.references and any(
        ref.url == rule.source_url and ref.consulted_on == rule.consulted_on
        for ref in rule.references
    ))


def _exclusion_reason(rule):
    conditions = {"wet": "carton mojado", "greasy": "carton con grasa", "painted": "carton pintado"}
    condition = next((label for name, label in conditions.items() if rule.conditions.get(name) is True), None)
    description = condition or (rule.presentation or rule.material.value).replace("_", " ")
    return f"El centro excluye explicitamente esta presentacion o condicion: {description}."


def compare_item(item: ConfirmedItem, center: Center) -> ComparisonResult:
    """Separar aceptacion de preparacion; sin regla suficiente se conserva la duda."""
    if not isinstance(item, ConfirmedItem) or not isinstance(center, Center):
        raise ReciclaClaroError(AppError(
            category="entrada_invalida", message="Se requieren un objeto confirmado y un centro.",
            retryable=False,
        ))
    missing = [name for name in ("material", "presentation") if _fact(item, name) is None]
    if item.material == Material.DESCONOCIDO and "material" not in missing:
        missing.append("material")
    if missing:
        return _result(item, center, "unknown", "Faltan datos confirmados del objeto.",
                       missing_data=_questions(missing))
    if item.material in _RESIN:
        resin = _fact(item, "resin_code")
        if resin != _RESIN[item.material]:
            return _result(item, center, "unknown", "Falta confirmar el codigo de resina o contradice el material.",
                           missing_data=_questions(["resin_code"]))

    full, partial = [], []
    for rule in center.rules:
        if rule.material != item.material:
            continue
        matches, missing = _matches(item, rule)
        if matches:
            (partial if missing else full).append((rule, missing))
    rejected = [r for r, _ in full if r.status == "no_admitido"]
    if rejected:
        if any(not _has_evidence(rule) for rule in rejected):
            return _result(item, center, "unknown", "La exclusion carece de fuentes suficientes.")
        return _result(item, center, "rejected", _exclusion_reason(rejected[0]), rejected)
    # Un conflicto documentado o una exclusion aun posible impide aceptar.
    uncertain = [r for r, _ in full if r.status == "pendiente"]
    possible_exclusions = [(r, names) for r, names in partial if r.status in {"no_admitido", "pendiente"}]
    if uncertain or possible_exclusions:
        names = [name for _, fields in possible_exclusions for name in fields]
        return _result(item, center, "unknown", "La evidencia requiere aclaracion antes de decidir.",
                       uncertain + [r for r, _ in possible_exclusions], missing_data=_questions(names))
    accepted = [r for r, _ in full if r.status == "aceptado"]
    if not accepted:
        return _result(item, center, "unknown", "No hay una regla suficiente para esta presentacion.",
                       [r for r, _ in partial],
                       missing_data=_questions([name for _, fields in partial for name in fields]))
    # Solo reglas con evidencia completa pueden justificar un resultado listo.
    if any(not _has_evidence(rule) for rule in accepted):
        return _result(item, center, "unknown", "La regla carece de identificador o fuentes suficientes.")
    missing, actions = [], []
    unverified_preparation = False
    instructions = []
    for rule in accepted:
        if rule.preparation and rule.preparation not in instructions:
            instructions.append(rule.preparation)
        for name, expected in rule.preparation_conditions.items():
            actual = _fact(item, name)
            if actual is None:
                missing.append(name)
            elif type(actual) is not type(expected) or actual != expected:
                action = rule.preparation or f"Cumplir la condicion documentada: {name}."
                if action not in actions:
                    actions.append(action)
        if rule.preparation and not rule.preparation_conditions:
            # Instruccion libre sin criterio verificable: nunca afirmar que se cumplio.
            if rule.preparation not in actions:
                actions.append(rule.preparation)
        elif not rule.preparation_conditions:
            unverified_preparation = True
    preparation_status = "action_required" if actions else (
        "unknown" if missing or unverified_preparation else "ready"
    )
    return _result(
        item, center, "accepted", "Aceptacion documentada para el material y la presentacion.", accepted,
        preparation_status=preparation_status, preparation_actions=actions,
        missing_data=_questions(missing), preparation=" ".join(instructions) or None,
    )


def compare_items(items: list[ConfirmedItem], center: Center) -> list[ComparisonResult]:
    """Comparar una entrada coherente; el orquestador construye el DeliveryPlan."""
    if not isinstance(center, Center) or not isinstance(items, list) or any(not isinstance(item, ConfirmedItem) for item in items):
        raise ReciclaClaroError(AppError(
            category="entrada_invalida", message="Se requiere una lista de objetos confirmados.", retryable=False,
        ))
    if len({item.item_id for item in items}) != len(items):
        raise ReciclaClaroError(AppError(
            category="entrada_invalida", message="Hay identificadores de objeto duplicados.", retryable=False,
        ))
    if len({(item.analysis_id, item.revision) for item in items}) > 1:
        raise ReciclaClaroError(AppError(
            category="entrada_invalida", message="Los objetos pertenecen a distintos analisis o revisiones.",
            retryable=False,
        ))
    return [compare_item(item, center) for item in items]
