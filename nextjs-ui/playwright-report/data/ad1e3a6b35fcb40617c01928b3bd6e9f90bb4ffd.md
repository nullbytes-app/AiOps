# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [ref=e3]:
    - img [ref=e6]
    - heading "Something went wrong" [level=1] [ref=e8]
    - paragraph [ref=e9]: We encountered an unexpected error. Please try again.
    - generic [ref=e10]:
      - generic [ref=e11]: "Error Details (Development Only):"
      - generic [ref=e12]: tenants.map is not a function
      - group [ref=e13]:
        - generic "Stack Trace" [ref=e14] [cursor=pointer]
    - generic [ref=e15]:
      - button "Try Again" [ref=e16] [cursor=pointer]:
        - img [ref=e17]
        - text: Try Again
      - button "Go Home" [active] [ref=e22] [cursor=pointer]:
        - img [ref=e23]
        - text: Go Home
    - paragraph [ref=e26]: If this problem persists, please contact support.
  - region "Notifications alt+T"
  - alert [ref=e27]
  - generic [ref=e30] [cursor=pointer]:
    - img [ref=e31]
    - generic [ref=e33]: 4 errors
    - button "Hide Errors" [ref=e34]:
      - img [ref=e35]
```