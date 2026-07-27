/** Role-based PII display — mirrors utils/pii.py (Admin = full; others masked). */

export function canViewFullPii(analyst?: { role?: string } | null): boolean {
  return analyst?.role === "Admin";
}

export function maskEmail(email: string): string {
  if (!email || !email.includes("@")) return email || "";
  const [local, domain] = email.split("@");
  if (!local) return `***@${domain}`;
  let masked: string;
  if (local.length === 1) masked = "*";
  else if (local.length === 2) masked = `${local[0]}*`;
  else masked = local.slice(0, 2) + "*".repeat(local.length - 2);
  return `${masked}@${domain}`;
}

export function maskPhone(phone: string): string {
  if (!phone) return "";
  const digits = String(phone).trim();
  if (digits.length <= 4) return "***";
  return digits.slice(0, 2) + "*".repeat(digits.length - 4) + digits.slice(-2);
}

export function maskStreet(street: string): string {
  if (!street) return "";
  const value = street.trim();
  if (value.length <= 2) return "*".repeat(value.length);
  return value.slice(0, 2) + "*".repeat(value.length - 2);
}

export function maskAddress(address: string): string {
  if (!address) return "";
  const value = address.trim();
  const idx = value.indexOf(",");
  if (idx >= 0) return maskStreet(value.slice(0, idx)) + value.slice(idx);
  return maskStreet(value);
}

export function maskIp(ip: string): string {
  if (!ip) return "";
  const parts = ip.split(".");
  if (parts.length === 4) return `${parts[0]}.${parts[1]}.***.***`;
  return "***";
}

export function displayPii(
  value: unknown,
  field: "email" | "phone" | "address" | "ip",
  analyst?: { role?: string } | null,
): string {
  if (value == null || value === "") return "";
  const str = String(value);
  if (canViewFullPii(analyst)) return str;
  if (field === "email") return maskEmail(str);
  if (field === "phone") return maskPhone(str);
  if (field === "address") return maskAddress(str);
  return maskIp(str);
}
