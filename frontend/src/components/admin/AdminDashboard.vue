<template>
  <div>
    <ul class="nav nav-tabs mb-3">
      <li class="nav-item" v-for="t in tabs" :key="t.id">
        <a class="nav-link" :class="{ active: tab === t.id }" href="#" @click.prevent="tab = t.id">{{ t.label }}</a>
      </li>
    </ul>

    <!-- Overview -->
    <div v-if="tab === 'overview'">
      <div v-if="!overview" class="text-muted">Loading...</div>
      <div v-else class="row g-3">
        <div class="col-md-3">
          <div class="card text-center"><div class="card-body">
            <div class="fs-3">{{ overview.total_students }}</div>
            <div class="text-muted">Students</div>
          </div></div>
        </div>
        <div class="col-md-3">
          <div class="card text-center"><div class="card-body">
            <div class="fs-3">{{ overview.total_companies }}</div>
            <div class="text-muted">Companies</div>
          </div></div>
        </div>
        <div class="col-md-3">
          <div class="card text-center"><div class="card-body">
            <div class="fs-3">{{ overview.drives.total }}</div>
            <div class="text-muted">Drives</div>
          </div></div>
        </div>
        <div class="col-md-3">
          <div class="card text-center"><div class="card-body">
            <div class="fs-3">{{ overview.applications.total }}</div>
            <div class="text-muted">Applications</div>
          </div></div>
        </div>

        <div class="col-md-6">
          <div class="card"><div class="card-body">
            <h6 class="card-title">Drives by status</h6>
            <ul class="list-unstyled mb-0">
              <li v-for="s in ['pending','approved','rejected','closed']" :key="s">
                {{ s }}: <strong>{{ overview.drives[s] }}</strong>
              </li>
            </ul>
          </div></div>
        </div>
        <div class="col-md-6">
          <div class="card"><div class="card-body">
            <h6 class="card-title">Companies by status</h6>
            <ul class="list-unstyled mb-0">
              <li v-for="s in ['pending','approved','rejected']" :key="s">
                {{ s }}: <strong>{{ overview.companies[s] }}</strong>
              </li>
            </ul>
          </div></div>
        </div>
      </div>
    </div>

    <!-- Companies -->
    <div v-if="tab === 'companies'">
      <div class="d-flex gap-2 mb-3">
        <input v-model="companyQuery" class="form-control" placeholder="Search by name/email" @input="loadCompanies" />
        <select v-model="companyStatus" class="form-select" style="max-width: 180px;" @change="loadCompanies">
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>
      <table class="table table-sm align-middle">
        <thead><tr><th>Company</th><th>Email</th><th>Status</th><th>Blacklisted</th><th></th></tr></thead>
        <tbody>
          <tr v-for="c in companies" :key="c.id">
            <td>{{ c.company_name }}</td>
            <td>{{ c.email }}</td>
            <td><span class="badge" :class="badgeClass(c.approval_status)">{{ c.approval_status }}</span></td>
            <td>{{ c.blacklisted ? "Yes" : "No" }}</td>
            <td class="text-end">
              <button v-if="c.approval_status !== 'approved'" class="btn btn-sm btn-success me-1" @click="approveCompany(c)">Approve</button>
              <button v-if="c.approval_status !== 'rejected'" class="btn btn-sm btn-outline-danger me-1" @click="rejectCompany(c)">Reject</button>
              <button class="btn btn-sm" :class="c.blacklisted ? 'btn-outline-secondary' : 'btn-outline-warning'" @click="toggleBlacklist(c.user_id, !c.blacklisted, loadCompanies)">
                {{ c.blacklisted ? "Unblacklist" : "Blacklist" }}
              </button>
            </td>
          </tr>
          <tr v-if="!companies.length"><td colspan="5" class="text-muted text-center">No companies found</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Drives -->
    <div v-if="tab === 'drives'">
      <div class="d-flex gap-2 mb-3">
        <input v-model="driveQuery" class="form-control" placeholder="Search by title/company" @input="loadDrives" />
        <select v-model="driveStatus" class="form-select" style="max-width: 180px;" @change="loadDrives">
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <table class="table table-sm align-middle">
        <thead><tr><th>Title</th><th>Company</th><th>Deadline</th><th>Status</th><th>Applicants</th><th></th></tr></thead>
        <tbody>
          <tr v-for="d in drives" :key="d.id">
            <td>{{ d.job_title }}</td>
            <td>{{ d.company_name }}</td>
            <td>{{ formatDate(d.application_deadline) }}</td>
            <td><span class="badge" :class="badgeClass(d.status)">{{ d.status }}</span></td>
            <td>{{ d.applicant_count }}</td>
            <td class="text-end">
              <button v-if="d.status !== 'approved'" class="btn btn-sm btn-success me-1" @click="approveDrive(d)">Approve</button>
              <button v-if="d.status !== 'rejected'" class="btn btn-sm btn-outline-danger" @click="rejectDrive(d)">Reject</button>
            </td>
          </tr>
          <tr v-if="!drives.length"><td colspan="6" class="text-muted text-center">No drives found</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Students -->
    <div v-if="tab === 'students'">
      <input v-model="studentQuery" class="form-control mb-3" placeholder="Search by name/email/branch" @input="loadStudents" />
      <table class="table table-sm align-middle">
        <thead><tr><th>Name</th><th>Email</th><th>Branch</th><th>CGPA</th><th>Grad year</th><th>Blacklisted</th><th></th></tr></thead>
        <tbody>
          <tr v-for="s in students" :key="s.id">
            <td>{{ s.name }}</td>
            <td>{{ s.email }}</td>
            <td>{{ s.branch }}</td>
            <td>{{ s.cgpa }}</td>
            <td>{{ s.grad_year }}</td>
            <td>{{ s.blacklisted ? "Yes" : "No" }}</td>
            <td class="text-end">
              <button class="btn btn-sm" :class="s.blacklisted ? 'btn-outline-secondary' : 'btn-outline-warning'" @click="toggleBlacklist(s.user_id, !s.blacklisted, loadStudents)">
                {{ s.blacklisted ? "Unblacklist" : "Blacklist" }}
              </button>
            </td>
          </tr>
          <tr v-if="!students.length"><td colspan="7" class="text-muted text-center">No students found</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Applications -->
    <div v-if="tab === 'applications'">
      <select v-model="applicationStatus" class="form-select mb-3" style="max-width: 220px;" @change="loadApplications">
        <option value="">All statuses</option>
        <option value="applied">Applied</option>
        <option value="shortlisted">Shortlisted</option>
        <option value="selected">Selected</option>
        <option value="rejected">Rejected</option>
      </select>
      <table class="table table-sm align-middle">
        <thead><tr><th>Student</th><th>Drive</th><th>Company</th><th>Status</th><th>Applied on</th></tr></thead>
        <tbody>
          <tr v-for="a in applications" :key="a.id">
            <td>{{ a.student_name }}</td>
            <td>{{ a.job_title }}</td>
            <td>{{ a.company_name }}</td>
            <td><span class="badge" :class="badgeClass(a.status)">{{ a.status }}</span></td>
            <td>{{ formatDate(a.application_date) }}</td>
          </tr>
          <tr v-if="!applications.length"><td colspan="5" class="text-muted text-center">No applications found</td></tr>
        </tbody>
      </table>
    </div>

    <!-- Stats -->
    <div v-if="tab === 'stats'">
      <div v-if="!statsData" class="text-muted">Loading...</div>
      <div v-else class="row g-3">
        <div class="col-md-4">
          <div class="card text-center"><div class="card-body">
            <div class="fs-3">{{ statsData.students_placed }} / {{ statsData.total_students }}</div>
            <div class="text-muted">Students placed ({{ (statsData.placement_rate * 100).toFixed(1) }}%)</div>
          </div></div>
        </div>
        <div class="col-md-4">
          <div class="card"><div class="card-body">
            <h6 class="card-title">Selected by branch</h6>
            <ul class="list-unstyled mb-0">
              <li v-for="(count, branch) in statsData.selected_by_branch" :key="branch">{{ branch }}: <strong>{{ count }}</strong></li>
            </ul>
            <p v-if="!Object.keys(statsData.selected_by_branch).length" class="text-muted mb-0">No selections yet</p>
          </div></div>
        </div>
        <div class="col-md-4">
          <div class="card"><div class="card-body">
            <h6 class="card-title">Selected by company</h6>
            <ul class="list-unstyled mb-0">
              <li v-for="(count, name) in statsData.selected_by_company" :key="name">{{ name }}: <strong>{{ count }}</strong></li>
            </ul>
            <p v-if="!Object.keys(statsData.selected_by_company).length" class="text-muted mb-0">No selections yet</p>
          </div></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
const badgeMap = {
  pending: "bg-warning text-dark",
  approved: "bg-success",
  rejected: "bg-danger",
  closed: "bg-secondary",
  applied: "bg-info text-dark",
  shortlisted: "bg-primary",
  selected: "bg-success",
};

export default {
  name: "AdminDashboard",
  data() {
    return {
      tab: "overview",
      tabs: [
        { id: "overview", label: "Overview" },
        { id: "companies", label: "Companies" },
        { id: "drives", label: "Drives" },
        { id: "students", label: "Students" },
        { id: "applications", label: "Applications" },
        { id: "stats", label: "Stats" },
      ],
      overview: null,
      companies: [],
      companyQuery: "",
      companyStatus: "",
      drives: [],
      driveQuery: "",
      driveStatus: "",
      students: [],
      studentQuery: "",
      applications: [],
      applicationStatus: "",
      statsData: null,
    };
  },
  watch: {
    tab(newTab) {
      this.loadTab(newTab);
    },
  },
  mounted() {
    this.loadTab(this.tab);
  },
  methods: {
    loadTab(tab) {
      if (tab === "overview") this.loadOverview();
      if (tab === "companies") this.loadCompanies();
      if (tab === "drives") this.loadDrives();
      if (tab === "students") this.loadStudents();
      if (tab === "applications") this.loadApplications();
      if (tab === "stats") this.loadStats();
    },
    badgeClass(status) {
      return badgeMap[status] || "bg-secondary";
    },
    formatDate(iso) {
      return iso ? new Date(iso).toLocaleString() : "-";
    },
    async loadOverview() {
      const res = await fetch("/api/admin/dashboard", { credentials: "same-origin" });
      this.overview = await res.json();
    },
    async loadCompanies() {
      const params = new URLSearchParams();
      if (this.companyQuery) params.set("q", this.companyQuery);
      if (this.companyStatus) params.set("status", this.companyStatus);
      const res = await fetch(`/api/admin/companies?${params}`, { credentials: "same-origin" });
      this.companies = await res.json();
    },
    async approveCompany(c) {
      await fetch(`/api/admin/companies/${c.id}/approve`, { method: "POST", credentials: "same-origin" });
      this.loadCompanies();
    },
    async rejectCompany(c) {
      await fetch(`/api/admin/companies/${c.id}/reject`, { method: "POST", credentials: "same-origin" });
      this.loadCompanies();
    },
    async loadDrives() {
      const params = new URLSearchParams();
      if (this.driveQuery) params.set("q", this.driveQuery);
      if (this.driveStatus) params.set("status", this.driveStatus);
      const res = await fetch(`/api/admin/drives?${params}`, { credentials: "same-origin" });
      this.drives = await res.json();
    },
    async approveDrive(d) {
      await fetch(`/api/admin/drives/${d.id}/approve`, { method: "POST", credentials: "same-origin" });
      this.loadDrives();
    },
    async rejectDrive(d) {
      await fetch(`/api/admin/drives/${d.id}/reject`, { method: "POST", credentials: "same-origin" });
      this.loadDrives();
    },
    async loadStudents() {
      const params = new URLSearchParams();
      if (this.studentQuery) params.set("q", this.studentQuery);
      const res = await fetch(`/api/admin/students?${params}`, { credentials: "same-origin" });
      this.students = await res.json();
    },
    async loadApplications() {
      const params = new URLSearchParams();
      if (this.applicationStatus) params.set("status", this.applicationStatus);
      const res = await fetch(`/api/admin/applications?${params}`, { credentials: "same-origin" });
      this.applications = await res.json();
    },
    async loadStats() {
      const res = await fetch("/api/admin/stats", { credentials: "same-origin" });
      this.statsData = await res.json();
    },
    async toggleBlacklist(userId, blacklisted, reload) {
      await fetch(`/api/admin/users/${userId}/blacklist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ blacklisted }),
      });
      reload();
    },
  },
};
</script>
