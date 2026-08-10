<template>
  <div class="card mx-auto" style="max-width: 480px;">
    <div class="card-body">
      <h5 class="card-title mb-3">Student registration</h5>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>

      <form @submit.prevent="submit">
        <div class="mb-3">
          <label class="form-label">Full name</label>
          <input v-model="form.name" type="text" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Email</label>
          <input v-model="form.email" type="email" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Password</label>
          <input v-model="form.password" type="password" class="form-control" required minlength="8" />
        </div>
        <div class="row">
          <div class="col-6 mb-3">
            <label class="form-label">Branch</label>
            <input v-model="form.branch" type="text" class="form-control" required />
          </div>
          <div class="col-6 mb-3">
            <label class="form-label">Graduation year</label>
            <input v-model.number="form.grad_year" type="number" class="form-control" min="2000" max="2100" required />
          </div>
        </div>
        <div class="mb-3">
          <label class="form-label">CGPA</label>
          <input v-model.number="form.cgpa" type="number" step="0.01" min="0" max="10" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Phone (optional)</label>
          <input v-model="form.phone" type="tel" class="form-control" />
        </div>
        <button type="submit" class="btn btn-primary w-100" :disabled="loading">
          {{ loading ? "Creating account..." : "Register" }}
        </button>
      </form>

      <hr />
      <p class="mb-0 text-center">
        Already have an account?
        <a href="#" @click.prevent="$emit('navigate', 'login')">Log in</a>
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: "RegisterStudent",
  emits: ["navigate", "logged-in"],
  data() {
    return {
      form: { name: "", email: "", password: "", branch: "", grad_year: null, cgpa: null, phone: "" },
      error: "",
      loading: false,
    };
  },
  methods: {
    async submit() {
      this.error = "";
      this.loading = true;
      try {
        const res = await fetch("/api/auth/register/student", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(this.form),
        });
        const body = await res.json();
        if (!res.ok) {
          this.error = body.error || "Registration failed";
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
