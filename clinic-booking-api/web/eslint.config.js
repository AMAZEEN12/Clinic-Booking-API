import tseslint from "typescript-eslint"
import jsxA11y from "eslint-plugin-jsx-a11y"
import reactHooks from "eslint-plugin-react-hooks"

export default tseslint.config(
tseslint.configs.recommended,
{
  files: ["**/*.{ts,tsx}"],
  plugins: {
    "jsx-a11y": jsxA11y,
    "react-hooks": reactHooks,
  },
  rules: {
    ...jsxA11y.configs.recommended.rules,
    ...reactHooks.configs.recommended.rules,
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "error",
  },
},
{
  ignores: ["dist/**", "node_modules/**"],
},
)