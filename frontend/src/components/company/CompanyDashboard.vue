<template>
  <div>
    <div v-if="company && company.approval_status !== 'approved'" class="alert alert-warning">
      Your company is <strong>{{ company.approval_status }}</strong>. You can browse this
      dashboard, but creating drives is locked until the admin approves your profile.
    </div>

    <ul class="nav nav-tabs mb-3">
      <li class="nav-item" v-for="t in tabs" :key="t.id">
        <a class="nav-link" :class="{ active: tab === t.id }" href="#" @click.prevent="selectTab(t.id)">{{ t.label }}</a>
      </li>
    </ul>

    <!-- Overview -->
    <div v-if="tab === 'overview'">
      <div v-if="!dashboard" class="text-muted">Loading...</div>
      <div v-else class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="card text-center"><div class="card-body">
            <div class="fs-3">{{ dashboard.drive_count }}</div>
            <div class="text-muted">Drives created</div>
          </div></div>
        </div>
        <div class="col-md-3">
          <div class="card text-center"><div class="card-body">
            <div class="fs-3">{{ dashboard.total_applicants }}</div>
            <div class="text-muted">Total applicants</div>
          </div></div>
        </div>
      </div>

      <table class="table table-sm align-middle" v-if="dashboard">
        <thead><tr><th>Title</th><th>Deadline</th><th>Status</th><th>Applicants</th><th></th></tr></thead>
        <tbody>
          <tr v-for="d in dashboard.drives" :key="d.id">
            <td>{{ d.job_title }}</td>
            <td>{{ formatDate(d.application_deadline) }}</td>
            <td><span class="badge" :class="badgeClass(d.status)">{{ d.status }}</span></td>
            <td>{{ d.applicant_count }}</td>
            <td class="text-end">
              <button class="btn btn-sm btn-outline-primary" @click="openApplicants(d)">View applicants</button>
            </td>
          </tr>
          <tr v-if="!dashboard.drives.length"><td colspan="5" class="text-muted text-center">No drives yet</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Profile -->
    <div v-if="tab === 'profile'">
      <div v-if="profileSaved" class="alert alert-success py-2">Profile updated.</div>
      <div v-if="profileError" class="alert alert-danger py-2">{{ profileError }}</div>
      <form @submit.prevent="saveProfile" class="col-md-6">
        <div class="mb-3">
          <label class="form-label">Company name</label>
          <input v-model="profileForm.company_name" type="text" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">HR contact name</label>
          <input v-model="profileForm.hr_contact_name" type="text" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">HR contact phone</label>
          <input v-model="profileForm.hr_contact_phone" type="tel" class="form-control" />
        </div>
        <div class="mb-3">
          <label class="form-label">Website</label>
          <input v-model="profileForm.website" type="url" class="form-control" />
        </div>
        <div class="mb-3">
          <label class="form-label">Description</label>
          <textarea v-model="profileForm.description" class="form-control" rows="3"></textarea>
        </div>
        <button type="submit" class="btn btn-primary" :disabled="profileSaving">
          {{ profileSaving ? "Saving..." : "Save" }}
        </button>
      </form>
    </div>

    <!-- Create Drive -->
    <div v-if="tab === 'create-drive'">
      <div v-if="company && company.approval_status !== 'approved'" class="alert alert-warning">
        Drive creation is locked until your company is approved.
      </div>
      <div v-if="driveError" class="alert alert-danger py-2">{{ driveError }}</div>
      <div v-if="driveCreated" class="alert alert-success py-2">Drive created and sent for admin approval.</div>

      <form @submit.prevent="createDrive" class="col-md-8">
        <div class="mb-3">
          <label class="form-label">Job title</label>
          <input v-model="driveForm.job_title" type="text" class="form-control" required :disabled="locked" />
        </div>
        <div class="mb-3">
          <label class="form-label">Job description</label>
          <textarea v-model="driveForm.job_description" class="form-control" rows="3" required :disabled="locked"></textarea>
        </div>
        <div class="row">
          <div class="col-md-6 mb-3">
            <label class="form-label">Eligible branches (comma-separated)</label>
            <input v-model="driveForm.eligible_branches" type="text" class="form-control" placeholder="CSE,ECE" required :disabled="locked" />
          </div>
          <div class="col-md-3 mb-3">
            <label class="form-label">Min CGPA</label>
            <input v-model.number="driveForm.min_cgpa" type="number" step="0.01" min="0" max="10" class="form-control" required :disabled="locked" />
          </div>
          <div class="col-md-3 mb-3">
            <label class="form-label">Eligible grad year</label>
            <input v-model.number="driveForm.eligible_grad_year" type="number" min="2000" max="2100" class="form-control" required :disabled="locked" />
          </div>
        </div>
        <div class="row">
          <div class="col-md-6 mb-3">
            <label class="form-label">Package / CTC (optional)</label>
            <input v-model="driveForm.package_ctc" type="text" class="form-control" :disabled="locked" />
          </div>
          <div class="col-md-6 mb-3">
            <label class="form-label">Application deadline</label>
            <input v-model="driveForm.application_deadline" type="datetime-local" class="form-control" required :disabled="locked" />
          </div>
        </div>
        <button type="submit" class="btn btn-primary" :disabled="locked || driveSaving">
          {{ driveSaving ? "Creating..." : "Create drive" }}
        </button>
      </form>
    </div>

    <!-- Applicants -->
    <div v-if="tab === 'applicants'">
      <div v-if="!selectedDrive" class="text-muted">Pick a drive from the Overview tab to view applicants.</div>
      <template v-else>
        <h5>{{ selectedDrive.job_title }}</h5>
        <select v-model="applicantStatusFilter" class="form-select mb-3" style="max-width: 220px;" @change="loadApplicants">
          <option value="">All statuses</option>
          <option value="applied">Applied</option>
          <option value="shortlisted">Shortlisted</option>
          <option value="selected">Selected</option>
          <option value="rejected">Rejected</option>
        </select>
        <table class="table table-sm align-middle">
          <thead><tr><th>Student</th><th>Branch</th><th>CGPA</th><th>Resume</th><th>Status</th><th>Interview</th><th></th></tr></thead>
          <tbody>
            <tr v-for="a in applicants" :key="a.id">
              <td>{{ a.student_name }}<br /><small class="text-muted">{{ a.student_email }}</small></td>
              <td>{{ a.branch }}</td>
              <td>{{ a.cgpa }}</td>
              <td>
                <a v-if="a.resume_path" :href="`/api/student/resume/${a.student_id}`" target="_blank">View</a>
                <span v-else class="text-muted">None</span>
              </td>
              <td>
                <select class="form-select form-select-sm" v-model="a.status" @change="updateApplication(a)">
                  <option value="applied">Applied</option>
                  <option value="shortlisted">Shortlisted</option>
                  <option value="selected">Selected</option>
                  <option value="rejected">Rejected</option>
                </select>
              </td>
              <td>
                <input type="datetime-local" class="form-control form-control-sm" v-model="a.interview_date_local" @change="updateApplication(a)" />
              </td>
              <td>
                <input type="text" class="form-control form-control-sm" placeholder="Remarks" v-model="a.remarks" @change="updateApplication(a)" />
              </td>
            </tr>
            <tr v-if="!applicants.length"><td colspan="7" class="text-muted text-center">No applicants yet</td></tr>
          </tbody>
        </table>
      </template>
    </div>
  </div>
</template>

<script>
const badgeMap = {
  pending: "bg-warning text-dark",
  approved: "bg-success",
  rejected: "bg-danger",
  closed: "bg-secondary",
};

function toLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default {
  name: "CompanyDashboard",
  data() {
    return {
      tab: "overview",
      tabs: [
        { id: "overview", label: "Overview" },
        { id: "profile", label: "Profile" },
        { id: "create-drive", label: "Create Drive" },
        { id: "applicants", label: "Applicants" },
      ],
      company: null,
      dashboard: null,
      profileForm: { company_name: "", hr_contact_name: "", hr_contact_phone: "", website: "", description: "" },
      profileSaved: false,
      profileError: "",
      profileSaving: false,
      driveForm: {
        job_title: "",
        job_description: "",
        eligible_branches: "",
        min_cgpa: null,
        eligible_grad_year: null,
        package_ctc: "",
        application_deadline: "",
      },
      driveError: "",
      driveCreated: false,
      driveSaving: false,
      selectedDrive: null,
      applicants: [],
      applicantStatusFilter: "",
    };
  },
  computed: {
    locked() {
      return this.company && this.company.approval_status !== "approved";
    },
  },
  async mounted() {
    await this.loadOverview();
  },
  methods: {
    selectTab(id) {
      this.tab = id;
      if (id === "overview") this.loadOverview();
    },
    badgeClass(status) {
      return badgeMap[status] || "bg-secondary";
    },
    formatDate(iso) {
      return iso ? new Date(iso).toLocaleString() : "-";
    },
    async loadOverview() {
      const res = await fetch("/api/company/dashboard", { credentials: "same-origin" });
      this.dashboard = await res.json();
      this.company = this.dashboard.company;
      this.profileForm = {
        company_name: this.company.company_name,
        hr_contact_name: this.company.hr_contact_name,
        hr_contact_phone: this.company.hr_contact_phone || "",
        website: this.company.website || "",
        description: this.company.description || "",
      };
    },
    async saveProfile() {
      this.profileSaved = false;
      this.profileError = "";
      this.profileSaving = true;
      try {
        const res = await fetch("/api/company/profile", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(this.profileForm),
        });
        const body = await res.json();
        if (!res.ok) {
          this.profileError = body.error || "Could not save profile";
          return;
        }
        this.company = body;
        this.profileSaved = true;
      } catch (e) {
        this.profileError = "Could not reach the server";
      } finally {
        this.profileSaving = false;
      }
    },
    async createDrive() {
      this.driveError = "";
      this.driveCreated = false;
      this.driveSaving = true;
      const payload = {
        ...this.driveForm,
        application_deadline: this.driveForm.application_deadline
          ? new Date(this.driveForm.application_deadline).toISOString()
          : "",
      };
      try {
        const res = await fetch("/api/company/drives", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        });
        const body = await res.json();
        if (!res.ok) {
          this.driveError = body.error || "Could not create drive";
          return;
        }
        this.driveCreated = true;
        this.driveForm = {
          job_title: "",
          job_description: "",
          eligible_branches: "",
          min_cgpa: null,
          eligible_grad_year: null,
          package_ctc: "",
          application_deadline: "",
        };
        this.loadOverview();
      } catch (e) {
        this.driveError = "Could not reach the server";
      } finally {
        this.driveSaving = false;
      }
    },
    openApplicants(drive) {
      this.selectedDrive = drive;
      this.tab = "applicants";
      this.applicantStatusFilter = "";
      this.loadApplicants();
    },
    async loadApplicants() {
      if (!this.selectedDrive) return;
      const params = new URLSearchParams();
      if (this.applicantStatusFilter) params.set("status", this.applicantStatusFilter);
      const res = await fetch(`/api/company/drives/${this.selectedDrive.id}/applications?${params}`, {
        credentials: "same-origin",
      });
      const data = await res.json();
      this.applicants = data.map((a) => ({ ...a, interview_date_local: toLocalInput(a.interview_date) }));
    },
    async updateApplication(a) {
      const payload = {
        status: a.status,
        interview_date: a.interview_date_local ? new Date(a.interview_date_local).toISOString() : null,
        remarks: a.remarks,
      };
      await fetch(`/api/company/applications/${a.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
    },
  },
};
</script>
