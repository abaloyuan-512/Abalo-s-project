self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

// Do not cache questions, readings, or private API responses on the device.
self.addEventListener("fetch", () => {});
