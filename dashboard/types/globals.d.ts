// Global type augmentations for the dashboard.
//
// Next.js normally generates CSS module declarations via its TS plugin, but
// side-effect CSS imports (`import "./globals.css"`) are not covered by any
// built-in type and surface as TS2882 under strict typechecking. Declare the
// non-module CSS side-effect import here.

declare module "*.css";
