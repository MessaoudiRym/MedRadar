// Same rules as the API (backend/app/schemas.py), checked while the user types.

export function passwordError(password: string): string | null {
  const bytes = new TextEncoder().encode(password).length;
  if (bytes < 8 || bytes > 72) return "Use 8 to 72 characters.";
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) return "Use at least one letter and one number.";
  return null;
}

/** "+213 550 12 34 56" and "0550-12-34-56" both become "0550123456". */
export function normalizePhone(phone: string): string {
  return phone.replace(/[\s.\-()]/g, "").replace(/^(\+|00)213/, "0");
}

export function phoneError(phone: string): string | null {
  const digits = normalizePhone(phone);
  if (/^0[567]\d{8}$/.test(digits) || /^0[2-4]\d{7}$/.test(digits)) return null;
  return "Enter an Algerian number, e.g. 0550 12 34 56 or 041 23 45 67.";
}

export function emailError(email: string): string | null {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim()) ? null : "Enter a valid email address.";
}

export function requiredError(value: string, label: string): string | null {
  return value.trim() ? null : `${label} is required.`;
}
