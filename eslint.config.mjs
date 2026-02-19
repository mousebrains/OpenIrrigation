import js from "@eslint/js";

const browserGlobals = {
  window: "readonly",
  document: "readonly",
  console: "readonly",
  setTimeout: "readonly",
  clearTimeout: "readonly",
  EventSource: "readonly",
  $: "readonly",
  Chart: "readonly",
};

const irrigationGlobals = {
  OI_timeouts: "writable",
  escapeHTML: "readonly",
  OI_clearTimeouts: "readonly",
  OI_timeDown: "readonly",
  OI_timeUpDown: "readonly",
  OI_toast: "readonly",
  OI_connectSSE: "readonly",
  OI_processSubmit: "readonly",
  OI_processForm: "readonly",
};

export default [
  { ignores: ["public_html/packages/**", "node_modules/**"] },
  js.configs.recommended,
  {
    files: ["public_html/js/irrigation.js"],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "script",
      globals: browserGlobals,
    },
    rules: {
      "no-unused-vars": ["warn", { args: "none", varsIgnorePattern: "^(OI_|escapeHTML)" }],
      "no-undef": "error",
      "eqeqeq": ["warn", "smart"],
      "no-redeclare": "error",
    },
  },
  {
    files: ["public_html/js/*.js"],
    ignores: ["public_html/js/irrigation.js"],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: "script",
      globals: { ...browserGlobals, ...irrigationGlobals },
    },
    rules: {
      "no-unused-vars": ["warn", { args: "none", varsIgnorePattern: "^(receivedStatus|statusSource|batchUpdate|batchCancel|buildActions|getStationName|getProgramName|inputChanged)" }],
      "no-undef": "error",
      "eqeqeq": ["warn", "smart"],
      "no-redeclare": "error",
    },
  },
];
