"""
Wallet policy — get and propose policy updates.
Policy validation logic for Privy TEE rules.
"""

try:
    from .common import wallet_request, logger
except ImportError:
    from common import wallet_request, logger

# ── Privy Policy Constants ───────────────────────────────────────────────────

VALID_EVM_METHODS = {
    "eth_sendTransaction", "eth_signTransaction", "eth_signTypedData_v4",
    "eth_signUserOperation", "eth_sign7702Authorization",
}
VALID_SOLANA_METHODS = {
    "signTransaction", "signAndSendTransaction", "signTransactionBytes",
}
VALID_ANY_METHODS = {"exportPrivateKey", "*"}
VALID_METHODS = VALID_EVM_METHODS | VALID_SOLANA_METHODS | VALID_ANY_METHODS

EVM_FIELD_SOURCES = {
    "ethereum_transaction", "ethereum_calldata",
    "ethereum_typed_data_domain", "ethereum_typed_data_message",
    "ethereum_7702_authorization",
}
SOLANA_FIELD_SOURCES = {
    "solana_program_instruction", "solana_system_program_instruction",
    "solana_token_program_instruction",
}
ANY_FIELD_SOURCES = {"system"}
VALID_FIELD_SOURCES = EVM_FIELD_SOURCES | SOLANA_FIELD_SOURCES | ANY_FIELD_SOURCES

VALID_OPERATORS = {"eq", "gt", "gte", "lt", "lte", "in", "in_condition_set"}

RULE_KEYS = {"name", "method", "conditions", "action"}
CONDITION_KEYS = {"field_source", "field", "operator", "value", "abi", "typed_data"}

FIELD_SOURCE_VALID_FIELDS = {
    "ethereum_typed_data_domain": {"chainId", "verifyingContract", "chain_id", "verifying_contract"},
    "ethereum_transaction": {"to", "value", "chain_id", "data", "gas", "gas_price", "max_fee_per_gas", "max_priority_fee_per_gas", "nonce"},
}

METHODS_REQUIRING_CONDITIONS = {"eth_signTypedData_v4"}

METHOD_FIELD_SOURCES = {
    "eth_sendTransaction":       {"ethereum_transaction", "ethereum_calldata", "system"},
    "eth_signTransaction":       {"ethereum_transaction", "ethereum_calldata", "system"},
    "eth_signUserOperation":     {"ethereum_transaction", "ethereum_calldata", "system"},
    "eth_signTypedData_v4":      {"ethereum_typed_data_domain", "ethereum_typed_data_message", "system"},
    "eth_sign7702Authorization": {"ethereum_7702_authorization", "system"},
    "signTransaction":           {"solana_program_instruction", "solana_system_program_instruction", "solana_token_program_instruction", "system"},
    "signAndSendTransaction":    {"solana_program_instruction", "solana_system_program_instruction", "solana_token_program_instruction", "system"},
    "signTransactionBytes":      {"solana_program_instruction", "solana_system_program_instruction", "solana_token_program_instruction", "system"},
    "exportPrivateKey":          {"system"},
    "*":                         {"system"},
}


def validate_and_clean_rules(rules: list, chain_type: str) -> tuple:
    """Validate rules against Privy schema. Returns (cleaned_rules, errors)."""
    errors = []
    cleaned = []

    for i, rule in enumerate(rules):
        prefix = f"Rule #{i + 1}"

        if not isinstance(rule, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        name = rule.get("name")
        if not name or not isinstance(name, str):
            errors.append(f"{prefix}: 'name' is required")

        method = rule.get("method")
        if not method or not isinstance(method, str):
            errors.append(f"{prefix}: 'method' is required")
        elif method not in VALID_METHODS:
            errors.append(f"{prefix}: unknown method '{method}'")
        else:
            if chain_type == "ethereum" and method in VALID_SOLANA_METHODS:
                errors.append(f"{prefix}: Solana method '{method}' invalid for ethereum")
            elif chain_type == "solana" and method in VALID_EVM_METHODS:
                errors.append(f"{prefix}: EVM method '{method}' invalid for solana")

        action = rule.get("action")
        if not action or not isinstance(action, str):
            errors.append(f"{prefix}: 'action' required (ALLOW or DENY)")
        else:
            action = action.upper()
            if action not in ("ALLOW", "DENY"):
                errors.append(f"{prefix}: 'action' must be ALLOW or DENY")

        conditions = rule.get("conditions") or []
        if not isinstance(conditions, list):
            errors.append(f"{prefix}: 'conditions' must be a list")
            conditions = []

        cleaned_conditions = []
        for j, cond in enumerate(conditions):
            cp = f"{prefix}, Cond #{j + 1}"
            if not isinstance(cond, dict):
                errors.append(f"{cp}: must be an object")
                continue

            fs = cond.get("field_source")
            if not fs:
                errors.append(f"{cp}: 'field_source' required")
            elif fs not in VALID_FIELD_SOURCES:
                errors.append(f"{cp}: unknown field_source '{fs}'")
            else:
                if chain_type == "ethereum" and fs in SOLANA_FIELD_SOURCES:
                    errors.append(f"{cp}: Solana field_source '{fs}' invalid for ethereum")
                elif chain_type == "solana" and fs in EVM_FIELD_SOURCES:
                    errors.append(f"{cp}: EVM field_source '{fs}' invalid for solana")
                if method and method in METHOD_FIELD_SOURCES:
                    allowed = METHOD_FIELD_SOURCES[method]
                    if fs not in allowed:
                        errors.append(f"{cp}: '{fs}' not valid for method '{method}'")

            field_val = cond.get("field")
            if not field_val:
                errors.append(f"{cp}: 'field' required")
            elif fs and fs in FIELD_SOURCE_VALID_FIELDS:
                if field_val not in FIELD_SOURCE_VALID_FIELDS[fs]:
                    errors.append(f"{cp}: field '{field_val}' invalid for '{fs}'")

            op = cond.get("operator")
            if not op:
                errors.append(f"{cp}: 'operator' required")
            elif op not in VALID_OPERATORS:
                errors.append(f"{cp}: unknown operator '{op}'")

            if "value" not in cond:
                errors.append(f"{cp}: 'value' required")
            else:
                value = cond["value"]
                if op == "in_condition_set":
                    errors.append(f"{cp}: 'in_condition_set' not supported, use 'in' with array")
                elif op == "in":
                    if not isinstance(value, list):
                        errors.append(f"{cp}: 'in' requires array")
                    elif len(value) > 100:
                        errors.append(f"{cp}: 'in' max 100 values")
                    else:
                        cond["value"] = [str(v) for v in value if v is not None]
                elif op and value is not None and not isinstance(value, str):
                    cond["value"] = str(value)

            cleaned_conditions.append({k: v for k, v in cond.items() if k in CONDITION_KEYS})

        if method and method in METHODS_REQUIRING_CONDITIONS and not cleaned_conditions:
            errors.append(f"{prefix}: method '{method}' requires at least one condition")

        cleaned_rule = {k: v for k, v in rule.items() if k in RULE_KEYS}
        cleaned_rule["conditions"] = cleaned_conditions
        if "action" in cleaned_rule and isinstance(cleaned_rule["action"], str):
            cleaned_rule["action"] = cleaned_rule["action"].upper()
        cleaned.append(cleaned_rule)

    return cleaned, errors


async def get_policy(chain_type: str = "ethereum") -> dict:
    """Get current wallet policy status."""
    return await wallet_request("GET", f"/agent/policy?chain_type={chain_type}")
