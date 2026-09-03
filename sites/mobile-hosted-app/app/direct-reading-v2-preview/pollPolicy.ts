export function shouldContinuePolling(httpStatus: number, terminal: boolean | undefined): boolean {
  return httpStatus >= 500 && terminal !== true;
}
