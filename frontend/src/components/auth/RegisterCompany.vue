<template>
  <div class="card mx-auto" style="max-width: 480px;">
    <div class="card-body">
      <h5 class="card-title mb-3">Company registration</h5>
      <p class="text-muted small">
        Your account is created immediately, but drive creation stays locked
        until the admin approves your company profile.
      </p>

      <div v-if="error" class="alert alert-danger py-2">{{ error }}</div>

      <form @submit.prevent="submit">
        <div class="mb-3">
          <label class="form-label">Your name</label>
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
        <div class="mb-3">
          <label class="form-label">Company name</label>
          <input v-model="form.company_name" type="text" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">HR contact name</label>
          <input v-model="form.hr_contact_name" type="text" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">HR contact phone (optional)</label>
          <input v-model="form.hr_contact_phone" type="tel" class="form-control" />
        </div>
        <div class="mb-3">
          <label class="form-label">Website (optional)</label>
          <input v-model="form.website" type="url" class="form-control" />
        </div>
        <div class="mb-3">
          <label class="form-label">Description (optional)</label>
          <textarea v-model="form.description" class="form-control" rows="2"></textarea>
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
  name: "RegisterCompany",
  emits: ["navigate", "logged-in"],
  data() {
    return {
      form: {
        name: "",
        email: "",
        password: "",
        company_name: "",
        hr_contact_name: "",
        hr_contact_phone: "",
        website: "",
        description: "",
      },
      error: "",
      loading: false,
    };
  },
  methods: {
    async submit() {
      this.error = "";
      this.loading = true;
      try {
        const res = await fetch("/api/auth/register/company", {
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
