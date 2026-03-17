export function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function readApiError(response) {
  let message = "Nao foi possivel concluir a operacao.";

  try {
    const payload = await response.json();
    message = payload?.message || payload?.code || message;
  } catch {
    message = `${message} (HTTP ${response.status})`;
  }

  return message;
}
