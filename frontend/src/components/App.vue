<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container">
      <span class="navbar-brand">Placement Portal</span>
      <div v-if="user" class="d-flex align-items-center text-light">
        <span class="me-3">{{ user.name }} ({{ user.role }})</span>
        <button class="btn btn-outline-light btn-sm" @click="logout">Log out</button>
      </div>
    </div>
  </nav>

  <div class="container mt-4">
    <div v-if="checkingSession" class="text-center text-muted">Loading...</div>

    <template v-else-if="!user">
      <Login v-if="page === 'login'" @navigate="page = $event" @logged-in="onAuthed" />
      <RegisterStudent v-else-if="page === 'register-student'" @navigate="page = $event" @logged-in="onAuthed" />
      <RegisterCompany v-else-if="page === 'register-company'" @navigate="page = $event" @logged-in="onAuthed" />
    </template>

    <template v-else>
      <AdminDashboard v-if="user.role === 'admin'" />
      <CompanyDashboard v-else-if="user.role === 'company'" />
      <StudentDashboard v-else-if="user.role === 'student'" />
    </template>
  </div>
</template>

<script>
import Login from "./auth/Login.vue";
import RegisterStudent from "./auth/RegisterStudent.vue";
import RegisterCompany from "./auth/RegisterCompany.vue";
import AdminDashboard from "./admin/AdminDashboard.vue";
import CompanyDashboard from "./company/CompanyDashboard.vue";
import StudentDashboard from "./student/StudentDashboard.vue";

export default {
  name: "App",
  components: { Login, RegisterStudent, RegisterCompany, AdminDashboard, CompanyDashboard, StudentDashboard },
  data() {
    return {
      user: null,
      page: "login",
      checkingSession: true,
    };
  },
  async mounted() {
    try {
      const res = await fetch("/api/auth/me", { credentials: "same-origin" });
      const body = await res.json();
      if (body.authenticated) this.user = body.user;
    } finally {
      this.checkingSession = false;
    }
  },
  methods: {
    onAuthed(user) {
      this.user = user;
    },
    async logout() {
      await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
      this.user = null;
      this.page = "login";
    },
  },
};
</script>
