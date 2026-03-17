export function maskCpf(value) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  const parts = [
    digits.slice(0, 3),
    digits.slice(3, 6),
    digits.slice(6, 9),
    digits.slice(9, 11),
  ];

  return [parts[0], parts[1], parts[2]].filter(Boolean).join(".") + (parts[3] ? `-${parts[3]}` : "");
}

export function normalizeDateInput(value) {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

export function toApiBirthDate(displayDate) {
  const match = displayDate.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!match) return "";

  const [, dd, mm, yyyy] = match;
  return `${yyyy}-${mm}-${dd}`;
}
