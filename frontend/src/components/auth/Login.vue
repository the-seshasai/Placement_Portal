<template>
  <div class="card mx-auto" style="max-width: 420px;">
    <div class="card-body">
      <h5 class="card-title mb-3">Log in</h5>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>

      <form @submit.prevent="submit">
        <div class="mb-3">
          <label class="form-label">Email</label>
          <input v-model="email" type="email" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input v-model="password" type="password" class="form-control" required minlength="8" />
        </div>
        <button type="submit" class="btn btn-primary w-100" :disabled="loading">
          {{ loading ? "Logging in..." : "Log in" }}
        </button>
      </form>

      <hr />
      <p class="mb-1 text-center">
        New student?
        <a href="#" @click.prevent="$emit('navigate', 'register-student')">Register</a>
      </p>
      <p class="mb-0 text-center">
        New company?
        <a href="#" @click.prevent="$emit('navigate', 'register-company')">Register</a>
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: "Login",
  emits: ["navigate", "logged-in"],
  data() {
    return { email: "", password: "", error: "", loading: false };
  },
  methods: {
    async submit() {
      this.error = "";
      this.loading = true;
      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify({ email: this.email, password: this.password }),
        });
        const body = await res.json();
        if (!res.ok) {
          this.error = body.error || "Login failed";
          return;
        }
        this.$emit("logged-in", body);
      } catch (e) {
        this.error = "Could not reach the server";
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>
