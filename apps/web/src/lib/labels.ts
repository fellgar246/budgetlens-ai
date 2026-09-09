import { copy } from "./copy";

export function accountTypeLabel(value: string): string {
  if (value === "revenue") return copy.accountTypeRevenue;
  if (value === "expense") return copy.accountTypeExpense;
  if (value === "asset") return copy.accountTypeAsset;
  if (value === "liability") return copy.accountTypeLiability;
  if (value === "equity") return copy.accountTypeEquity;
  if (value === "other") return copy.accountTypeOther;
  return value;
}

export function dimensionStatusLabel(value: string): string {
  if (value === "active") return copy.active;
  if (value === "inactive") return copy.statusInactive;
  if (value === "archived") return copy.archived;
  return value;
}

export function versionStatusLabel(value: string): string {
  if (value === "draft") return copy.draft;
  if (value === "published") return copy.published;
  if (value === "archived") return copy.archived;
  return value;
}

export function memberRoleLabel(value: string): string {
  if (value === "viewer") return copy.roleViewer;
  if (value === "analyst") return copy.roleAnalyst;
  if (value === "admin") return copy.roleAdmin;
  return value;
}

export function memberStatusLabel(value: string): string {
  if (value === "active") return copy.active;
  if (value === "inactive") return copy.statusInactive;
  if (value === "disabled") return copy.statusDisabled;
  return value;
}

export function scenarioStatusLabel(value: string): string {
  if (value === "saved") return copy.savedState;
  if (value === "archived") return copy.archived;
  if (value === "draft") return copy.draft;
  return value;
}

export function baselineTypeLabel(value: string): string {
  if (value === "budget") return copy.importBudget;
  if (value === "actual") return copy.importActual;
  return value;
}

export function importFieldLabel(field: string): string {
  switch (field) {
    case "period":
      return copy.periodLabel;
    case "account_code":
      return copy.fieldAccountCode;
    case "account_name":
      return copy.fieldAccountName;
    case "account_type":
      return copy.fieldAccountType;
    case "department_code":
      return copy.fieldDepartmentCode;
    case "department_name":
      return copy.fieldDepartmentName;
    case "cost_center_code":
      return copy.fieldCostCenterCode;
    case "cost_center_name":
      return copy.fieldCostCenterName;
    case "amount":
      return copy.fieldAmount;
    case "currency":
      return copy.fieldCurrency;
    case "source_reference":
      return copy.fieldSourceReference;
    default:
      return field;
  }
}

export function groupByLabel(groupBy: string): string {
  if (groupBy === "account") return copy.groupByAccount;
  if (groupBy === "cost_center") return copy.groupByCostCenter;
  return copy.groupByDepartment;
}

export function sortCaption(sort: string): string {
  return sort === "variance_amount" ? copy.sortVarianceOrder : copy.sortOrderLabel;
}

export function sortOptionLabel(sort: string): string {
  return sort === "variance_amount" ? copy.sortVariance : copy.sortUnfavorable;
}
