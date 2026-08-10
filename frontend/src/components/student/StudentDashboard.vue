<template>
  <div>
    <ul class="nav nav-tabs mb-3">
      <li class="nav-item" v-for="t in tabs" :key="t.id">
        <a class="nav-link" :class="{ active: tab === t.id }" href="#" @click.prevent="selectTab(t.id)">{{ t.label }}</a>
      </li>
    </ul>

    <!-- Browse Drives -->
    <div v-if="tab === 'drives'">
      <div v-if="applyError" class="alert alert-danger py-2">{{ applyError }}</div>
      <div class="d-flex gap-2 mb-3">
        <input v-model="driveQuery" class="form-control" placeholder="Search by title/company" @input="loadDrives" />
        <div class="form-check form-switch d-flex align-items-center">
          <input class="form-check-input me-2" type="checkbox" v-model="eligibleOnly" @change="loadDrives" id="eligibleOnly" />
          <label class="form-check-label text-nowrap" for="eligibleOnly">Eligible only</label>
        </div>
      </div>
      <table class="table table-sm align-middle">
        <thead><tr><th>Title</th><th>Company</th><th>Package</th><th>Deadline</th><th>Eligible</th><th>Status</th><th></th></tr></thead>
        <tbody>
          <tr v-for="d in drives" :key="d.id">
            <td>{{ d.job_title }}</td>
            <td>{{ d.company_name }}</td>
            <td>{{ d.package_ctc || "-" }}</td>
            <td>{{ formatDate(d.application_deadline) }}</td>
            <td>
              <span class="badge" :class="d.eligible ? 'bg-success' : 'bg-secondary'">{{ d.eligible ? "Yes" : "No" }}</span>
            </td>
            <td>
              <span v-if="d.already_applied" class="badge" :class="badgeClass(d.application_status)">{{ d.application_status }}</span>
              <span v-else class="text-muted">-</span>
            </td>
            <td class="text-end">
              <button
                v-if="!d.already_applied"
                class="btn btn-sm btn-primary"
                :disabled="!d.eligible"
                @click="apply(d)"
              >
                Apply
              </button>
            </td>
          </tr>
          <tr v-if="!drives.length"><td colspan="7" class="text-muted text-center">No drives found</td></tr>
        </tbody>
      </table>
    </div>

    <!-- My Applications -->
    <div v-if="tab === 'applications'">
      <div class="d-flex align-items-center gap-2 mb-3">
        <button class="btn btn-outline-secondary btn-sm" :disabled="exportStatus === 'pending'" @click="startExport">
          {{ exportStatus === "pending" ? "Preparing export..." : "Export applications (CSV)" }}
        </button>
        <a v-if="exportStatus === 'ready'" class="btn btn-success btn-sm" href="/api/student/applications/export/download">
          Download CSV
        </a>
        <span v-if="exportStatus === 'failed'" class="text-danger small">Export failed, try again.</span>
      </div>
      <table class="table table-sm align-middle">
        <thead><tr><th>Title</th><th>Company</th><th>Status</th><th>Applied on</th><th>Interview</th></tr></thead>
        <tbody>
          <tr v-for="a in applications" :key="a.id">
            <td>{{ a.job_title }}</td>
            <td>{{ a.company_name }}</td>
            <td><span class="badge" :class="badgeClass(a.status)">{{ a.status }}</span></td>
            <td>{{ formatDate(a.application_date) }}</td>
            <td>{{ a.interview_date ? formatDate(a.interview_date) : "-" }}</td>
          </tr>
          <tr v-if="!applications.length"><td colspan="5" class="text-muted text-center">No applications yet</td></tr>
        </tbody>
      </table>
    </div>

    <!-- History -->
    <div v-if="tab === 'history'">
      <table class="table table-sm align-middle">
        <thead><tr><th>Title</th><th>Company</th><th>Outcome</th><th>Applied on</th></tr></thead>
        <tbody>
          <tr v-for="a in history" :key="a.id">
            <td>{{ a.job_title }}</td>
            <td>{{ a.company_name }}</td>
            <td><span class="badge" :class="badgeClass(a.status)">{{ a.status }}</span></td>
            <td>{{ formatDate(a.application_date) }}</td>
          </tr>
          <tr v-if="!history.length"><td colspan="4" class="text-muted text-center">No finalized applications yet</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Profile -->
    <div v-if="tab === 'profile'">
      <div v-if="profileSaved" class="alert alert-success py-2">Profile updated.</div>
      <div v-if="profileError" class="alert alert-danger py-2">{{ profileError }}</div>
      <form @submit.prevent="saveProfile" class="col-md-6 mb-4">
        <div class="row">
          <div class="col-6 mb-3">
            <label class="form-label">Branch</label>
            <input v-model="profileForm.branch" type="text" class="form-control" required />
          </div>
          <div class="col-6 mb-3">
            <label class="form-label">Graduation year</label>
            <input v-model.number="profileForm.grad_year" type="number" min="2000" max="2100" class="form-control" required />
          </div>
        </div>
        <div class="mb-3">
          <label class="form-label">CGPA</label>
          <input v-model.number="profileForm.cgpa" type="number" step="0.01" min="0" max="10" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Phone</label>
          <input v-model="profileForm.phone" type="tel" class="form-control" />
        </div>
        <button type="submit" class="btn btn-primary" :disabled="profileSaving">
          {{ profileSaving ? "Saving..." : "Save" }}
        </button>
      </form>

      <h6>Resume</h6>
      <div v-if="resumeError" class="alert alert-danger py-2">{{ resumeError }}</div>
      <p v-if="profileForm.resume_path">
        Current resume: <a :href="`/api/student/resume/${profileId}`" target="_blank">View</a>
      </p>
      <p v-else class="text-muted">No resume uploaded yet.</p>
      <form @submit.prevent="uploadResume" class="d-flex gap-2">
        <input type="file" class="form-control" style="max-width: 320px;" @change="onFileChange" accept=".pdf,.doc,.docx" required />
        <button type="submit" class="btn btn-outline-primary" :disabled="!resumeFile || resumeUploading">
          {{ resumeUploading ? "Uploading..." : "Upload" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
const badgeMap = {
  applied: "bg-info text-dark",
  shortlisted: "bg-primary",
  selected: "bg-success",
  rejected: "bg-danger",
};

export default {
  name: "StudentDashboard",
  data() {
    return {
      tab: "drives",
      tabs: [
        { id: "drives", label: "Browse Drives" },
        { id: "applications", label: "My Applications" },
        { id: "history", label: "Placement History" },
        { id: "profile", label: "Profile" },
      ],
      drives: [],
      driveQuery: "",
      eligibleOnly: false,
      applyError: "",
      applications: [],
      history: [],
      profileId: null,
      profileForm: { branch: "", cgpa: null, grad_year: null, phone: "", resume_path: null },
      profileSaved: false,
      profileError: "",
      profileSaving: false,
      resumeFile: null,
      resumeError: "",
      resumeUploading: false,
      exportStatus: "none",
      exportPollHandle: null,
    };
  },
  async mounted() {
    await this.loadProfile();
    await this.loadDrives();
  },
  beforeUnmount() {
    if (this.exportPollHandle) clearInterval(this.exportPollHandle);
  },
  methods: {
    selectTab(id) {
      this.tab = id;
      if (id === "drives") this.loadDrives();
      if (id === "applications") {
        this.loadApplications();
        this.checkExportStatus();
      }
      if (id === "history") this.loadHistory();
    },
    badgeClass(status) {
      return badgeMap[status] || "bg-secondary";
    },
    formatDate(iso) {
      return iso ? new Date(iso).toLocaleString() : "-";
    },
    async loadProfile() {
      const res = await fetch("/api/student/profile", { credentials: "same-origin" });
      const data = await res.json();
      this.profileId = data.id;
      this.profileForm = {
        branch: data.branch,
        cgpa: data.cgpa,
        grad_year: data.grad_year,
        phone: data.phone || "",
        resume_path: data.resume_path,
      };
    },
    async saveProfile() {
      this.profileSaved = false;
      this.profileError = "";
      this.profileSaving = true;
      try {
        const res = await fetch("/api/student/profile", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(this.profileForm),
        });
        const data = await res.json();
        if (!res.ok) {
          this.profileError = data.error || "Could not save profile";
          return;
        }
        this.profileForm.resume_path = data.resume_path;
        this.profileSaved = true;
      } catch (e) {
        this.profileError = "Could not reach the server";
      } finally {
        this.profileSaving = false;
      }
    },
    onFileChange(e) {
      this.resumeFile = e.target.files[0] || null;
    },
    async uploadResume() {
      this.resumeError = "";
      if (!this.resumeFile) return;
      this.resumeUploading = true;
      try {
        const form = new FormData();
        form.append("resume", this.resumeFile);
        const res = await fetch("/api/student/resume", {
          method: "POST",
          credentials: "same-origin",
          body: form,
        });
        const body = await res.json();
        if (!res.ok) {
          this.resumeError = body.error || "Upload failed";
          return;
        }
        this.profileForm.resume_path = body.resume_path;
        this.resumeFile = null;
      } catch (e) {
        this.resumeError = "Could not reach the server";
      } finally {
        this.resumeUploading = false;
      }
    },
    async loadDrives() {
      const params = new URLSearchParams();
      if (this.driveQuery) params.set("q", this.driveQuery);
      if (this.eligibleOnly) params.set("eligible_only", "true");
      const res = await fetch(`/api/student/drives?${params}`, { credentials: "same-origin" });
      this.drives = await res.json();
    },
    async apply(drive) {
      this.applyError = "";
      try {
        const res = await fetch(`/api/student/drives/${drive.id}/apply`, {
          method: "POST",
          credentials: "same-origin",
        });
        const body = await res.json();
        if (!res.ok) {
          this.applyError = body.error || "Could not apply";
          return;
        }
        this.loadDrives();
      } catch (e) {
        this.applyError = "Could not reach the server";
      }
    },
    async loadApplications() {
      const res = await fetch("/api/student/applications", { credentials: "same-origin" });
      this.applications = await res.json();
    },
    async startExport() {
      await fetch("/api/student/applications/export", { method: "POST", credentials: "same-origin" });
      this.exportStatus = "pending";
      if (this.exportPollHandle) clearInterval(this.exportPollHandle);
      this.exportPollHandle = setInterval(this.checkExportStatus, 3000);
    },
    async checkExportStatus() {
      const res = await fetch("/api/student/applications/export/status", { credentials: "same-origin" });
      const body = await res.json();
      this.exportStatus = body.status;
      if ((body.status === "ready" || body.status === "failed") && this.exportPollHandle) {
        clearInterval(this.exportPollHandle);
        this.exportPollHandle = null;
      }
    },
    async loadHistory() {
      const res = await fetch("/api/student/history", { credentials: "same-origin" });
      this.history = await res.json();
    },
  },
};
</script>
