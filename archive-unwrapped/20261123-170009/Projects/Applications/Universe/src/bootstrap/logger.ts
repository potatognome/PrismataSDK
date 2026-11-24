function pad2(value: number): string {
  return value < 10 ? `0${value}` : `${value}`;
}

function utcTimestamp(): string {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = pad2(now.getUTCMonth() + 1);
  const day = pad2(now.getUTCDate());
  const hour = pad2(now.getUTCHours());
  const minute = pad2(now.getUTCMinutes());
  const second = pad2(now.getUTCSeconds());
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

export function bootstrapLog(message: string): void {
  // Emit a bordered, color-coded UTC log line that mirrors tUilKit style.
  const ts = utcTimestamp();
  const border = "============================================================";
  const cyan = "\u001b[36m";
  const yellow = "\u001b[33m";
  const reset = "\u001b[0m";

  console.log(`${cyan}${border}${reset}`);
  console.log(`${yellow}[Universe][${ts}]${reset} ${message}`);
  console.log(`${cyan}${border}${reset}`);
}
