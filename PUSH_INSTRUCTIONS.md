# Push Instructions — Musubi

Workflow GitHub-first ke Hugging Face Space. Pilih satu opsi sync (manual atau auto via GitHub Actions).

> Final QA checklist ada di bagian akhir file ini.

---

## Section A — Setup GitHub (wajib)

```bash
git init
git add .
git commit -m "Initial commit: Musubi v1.0"
```

Buat repo baru di <https://github.com/new>:
- Repository name: `musubi`
- Visibility: **public**
- **Jangan** tambahkan README / .gitignore / license (sudah ada di local)

```bash
git remote add origin https://github.com/<username>/musubi.git
git branch -M main
git push -u origin main
```

---

## Section B — Setup Hugging Face Space

1. Buat Space baru di <https://huggingface.co/new-space>:
   - Owner: `lumicero`
   - Space name: `musubi`
   - SDK: **Docker**
   - Hardware: **CPU basic** (free)
   - Visibility: **public**
2. Buka tab **Settings → Variables and secrets**.
3. Tambahkan secret `ENTREZ_EMAIL` dengan value email kamu (dipakai oleh NCBI Entrez API).

---

## Section C — Opsi 1: Dual remote (manual sync)

Cocok kalau update jarang. Push sekali ke GitHub, push sekali ke HF Space.

```bash
git remote add space https://huggingface.co/spaces/lumicero/musubi
git push space main
```

Untuk update berikutnya:

```bash
git push origin main && git push space main
```

> Catatan: butuh **HF access token** kalau Space private (atau di-block oleh password prompt). Generate di <https://huggingface.co/settings/tokens> (scope **Write**) dan pakai sebagai password saat push pertama. Username adalah HF username.

---

## Section C — Opsi 2: GitHub Actions auto-sync (recommended)

Cocok kalau update sering. Setiap push ke `main` GitHub auto-sync ke HF Space dalam ~30 detik.

1. Buat file `.github/workflows/sync-to-hf-space.yml`:

   ```yaml
   name: Sync to Hugging Face Space
   on:
     push:
       branches: [main]
     workflow_dispatch:
   jobs:
     sync:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0
             lfs: true
         - name: Push to HF Space
           env:
             HF_TOKEN: ${{ secrets.HF_TOKEN }}
           run: |
             git push --force https://lumicero:$HF_TOKEN@huggingface.co/spaces/lumicero/musubi main
   ```

2. Buat HF access token (**Write** scope) di <https://huggingface.co/settings/tokens>.
3. Di GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**. Tambah `HF_TOKEN` dengan value token tersebut.
4. **Push manual pertama tetap perlu** (pakai Opsi 1) supaya Space tahu branch `main`-nya. Setelah itu Actions take over.

---

## Section D — Verifikasi

1. Buka URL Space: <https://huggingface.co/spaces/lumicero/musubi>
2. Tunggu build selesai (5–10 menit pertama; rebuild lebih cepat).
3. Cek **Logs** kalau ada error build.
4. Tes UI di browser: paste sample abstract, klik Analyze, eksplor graph.

---

## Final QA checklist

Jalankan sebelum push pertama ke HF Space. Cek lokal dulu:

```bash
docker build -t musubi .
docker run -p 7860:7860 -e ENTREZ_EMAIL=test@example.com musubi
```

Buka <http://localhost:7860> dan verifikasi:

- [ ] `/health` responds 200 dengan `model_loaded: true`
- [ ] `/analyze` dengan 1 abstract returns valid graph
- [ ] `/analyze` dengan 5 abstract returns valid graph dalam < 30 detik
- [ ] `/pubmed-search` returns abstracts (dengan `ENTREZ_EMAIL` di-set)
- [ ] Graph node click highlights neighbors
- [ ] Edge click opens evidence panel
- [ ] Confidence slider re-triggers analyze (debounced)
- [ ] Pair-type filter updates graph instantly (tanpa re-fetch)
- [ ] Granularity toggle re-triggers analyze
- [ ] No console errors di browser
- [ ] Dark theme konsisten di semua component
