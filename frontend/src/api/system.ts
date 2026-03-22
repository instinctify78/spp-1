import type { Device } from "./types";

export const systemApi = {
  gpus: async (): Promise<Device[]> => {
    const res = await fetch("/system/gpus");
    if (!res.ok) throw new Error("Failed to fetch GPU list");
    const data = (await res.json()) as { devices: Device[] };
    return data.devices;
  },
};
