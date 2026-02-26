export async function startAutomation() {
  const response = await fetch("/automation/execute", { method: "POST" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || response.statusText);
  }
  return response.json();
}

export async function cancelAutomation() {
  const response = await fetch("/automation/cancel", { method: "POST" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || response.statusText);
  }
  return response.json();
}

export async function getAutomationStatus() {
  const response = await fetch("/automation/status");
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || response.statusText);
  }
  return response.json();
}
