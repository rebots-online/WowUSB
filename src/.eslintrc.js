module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  plugins: [
    "@typescript-eslint/parser",
    "@typescript-eslint/parser-services",
    "@typescript-eslint/eslint-plugin-react",
    "@typescript-eslint/eslint-plugin-hooks",
    "@typescript-eslint/eslint-plugin-jsx"
  ],
  extends: [
    "plugin:@typescript-eslint/eslint-plugin-react@latest",
    "plugin:@typescript-eslint/eslint-plugin-react-hooks@latest",
    "plugin:@typescript-eslint/eslint-plugin-jsx@latest"
  ],
  env: {
    node: true
    es2024: {
      envs: {
        node: true
        browser: true
        jest: true
      }
    },
    2024: {
      globals: {
        console: true,
        fetch: true
      }
    },
    2023: {
      globals: {
        console: true
      }
    },
    2022: {
      globals: {
        console: true
      }
    },
     },
     },
    },
  rules: {
      "react-hooks/exhaustive-deps": [
        "error"
      ],
      "react-hooks/rules-of-hooks": [
        "error"
      ],
      "react-hooks/rules-of-hooks": [
        "error"
      ],
      "react-hooks/exhaustive-deps": [
        "error"
      ],
      "react-hooks/rules-of-hooks": [
        "error"
      ]
    },
    "react-hooks/rules-of-hooks": [
      "error"
    ],
    "react-hooks/exhaustive-deps": [
      "error"
    ],
    "react-hooks/rules-of-hooks": [
      "error"
    ],
    "react-hooks/exhaustive-deps": [
      "error"
    ],
    "react-hooks/exhaustive-deps": [
      "error"
    ]
    ],
    "react-hooks/rules-of-hooks": [
      "error"
    ],
    "react-hooks/exhaustive-deps": [
      "error"
    ]
  }
}