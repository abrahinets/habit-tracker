import { Plugin } from "@opencode/plugin"

const BLOCKED_PATTERNS = ["rm -rf", "git push --force"]

export default Plugin.define({
  id: "guard",
  async setup(ctx) {
    await ctx.tool.hook("execute.before", (event) => {
      if (event.tool !== "bash" && event.tool !== "shell") return

      const command = String(event.input?.command ?? "")
      const pattern = BLOCKED_PATTERNS.find((value) => command.includes(value))
      if (pattern) {
        throw new Error(
          `Blocked by guard: the command contains "${pattern}". ` +
            "Run it manually if this is intentional.",
        )
      }
    })
  },
})
