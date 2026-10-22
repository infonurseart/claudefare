export const NURSEART_ENV = import.meta.env.VITE_NURSEART_ENV || "demo";
export const IS_DEMO = NURSEART_ENV === "demo";
export const IS_PILOT = NURSEART_ENV === "pilot";
export const IS_PRODUCTION = NURSEART_ENV === "production";

export const ENV_LABELS = {
  demo: "DEMOSTRACIÓN · datos ficticios",
  pilot: "PILOTO · acceso autorizado",
  production: "PRODUCCIÓN",
};
