# 🚀 QUICK START GUIDE - WINDOWING METHODS

## ⚡ TL;DR (30 seconds)

```bash
# 1. Compile all 5 window variants
make all

# 2. Run the one you want
./signal_analyzer_triangular adc_data/535g20250502pm427ms20hz69.txt

# Done! Creates: filtered_triangular_535g20250502pm427ms20hz69.txt
```

---

## 📦 What You Got

**5 Complete DSP Programs** (each with different window):
- ✅ `signal_analyzer_triangular` - Triangular window
- ✅ `signal_analyzer_rectangular` - Rectangular window  
- ✅ `signal_analyzer_hamming` - Hamming window
- ✅ `signal_analyzer_hanning` - Hanning window
- ✅ `signal_analyzer_blackman` - Blackman window

---

## 🛠️ Step 1: Compile

### **Option A: Compile All (Recommended)**
```bash
make all
```

Output:
```
[Compiling] TRIANGULAR window variant...
✓ signal_analyzer_triangular created
[Compiling] RECTANGULAR window variant...
✓ signal_analyzer_rectangular created
[Compiling] HAMMING window variant...
✓ signal_analyzer_hamming created
[Compiling] HANNING window variant...
✓ signal_analyzer_hanning created
[Compiling] BLACKMAN window variant...
✓ signal_analyzer_blackman created

✓ All windowing variants compiled successfully!
```

### **Option B: Compile One Only**
```bash
make triangular      # just triangular
# or
make hamming         # just hamming
```

---

## 🎯 Step 2: Run

### **Choose Your Window Type**

**Triangular (Moderate spectral performance)**
```bash
./signal_analyzer_triangular adc_data/your_file.txt
```

**Rectangular (Sharp cutoff for sinusoids)**
```bash
./signal_analyzer_rectangular adc_data/your_file.txt
```

**Hamming (Best general purpose)**
```bash
./signal_analyzer_hamming adc_data/your_file.txt
```

**Hanning (Better side lobe rolloff)**
```bash
./signal_analyzer_hanning adc_data/your_file.txt
```

**Blackman (Excellent side lobe suppression)**
```bash
./signal_analyzer_blackman adc_data/your_file.txt
```

---

## 📊 Step 3: Use Results

Each program creates an output file:
```
filtered_<window_name>_your_file.txt
```

Examples:
```
filtered_triangular_535g20250502pm427ms20hz69.txt
filtered_rectangular_535g20250502pm427ms20hz69.txt
filtered_hamming_535g20250502pm427ms20hz69.txt
filtered_hanning_535g20250502pm427ms20hz69.txt
filtered_blackman_535g20250502pm427ms20hz69.txt
```

---

## 📈 Step 4: Visualize (Optional)

View results with your existing plotting script:
```bash
python3 main_plot_program.py your_file.txt
```

---

## 🔄 Using with new_run.sh (Automation)

Edit `new_run.sh` line 12 to select window:

```bash
# BEFORE (original, using fixed analyzer)
C_PROGRAM="./signal_analyzer_fixed"

# AFTER (using hamming window)
C_PROGRAM="./signal_analyzer_hamming"

# Or use any other:
C_PROGRAM="./signal_analyzer_triangular"
C_PROGRAM="./signal_analyzer_rectangular"
C_PROGRAM="./signal_analyzer_hanning"
C_PROGRAM="./signal_analyzer_blackman"
```

Then run:
```bash
./new_run.sh
```

---

## 🧪 Test Example

**Process single file with all 5 windows:**

```bash
# Compile all
make all

# Process same file with each window
./signal_analyzer_triangular adc_data/sample.txt
./signal_analyzer_rectangular adc_data/sample.txt
./signal_analyzer_hamming adc_data/sample.txt
./signal_analyzer_hanning adc_data/sample.txt
./signal_analyzer_blackman adc_data/sample.txt

# See all results
ls filtered_*.txt
```

---

## 📚 Window Functions at a Glance

| Window | Use Case | Characteristics |
|--------|----------|-----------------|
| **Triangular** | General purpose | Moderate performance |
| **Rectangular** | Sinusoids | Sharpest cutoff |
| **Hamming** | ⭐ Default choice | Good balance |
| **Hanning** | Better performance | Lower side lobes |
| **Blackman** | 🏆 Best quality | Excellent suppression |

---

## 🛡️ Safeguards

✅ Original file backed up as `signal_analyzer_fixed.c.backup`  
✅ All original files unchanged  
✅ Each window has its own executable  
✅ No conflicts or overwrites  
✅ Easy to revert: delete new files, keep backup

---

## 🎓 Files Reference

| File | Purpose |
|------|---------|
| `signal_analyzer_triangular.c` | Triangular window implementation |
| `signal_analyzer_rectangular.c` | Rectangular window implementation |
| `signal_analyzer_hamming.c` | Hamming window implementation |
| `signal_analyzer_hanning.c` | Hanning window implementation |
| `signal_analyzer_blackman.c` | Blackman window implementation |
| `Makefile` | Build system (use `make`) |
| `WINDOWING_IMPLEMENTATION_GUIDE.md` | Detailed documentation |
| `IMPLEMENTATION_SUMMARY.md` | Complete summary |
| `signal_analyzer_fixed.c.backup` | Original backup |

---

## ❓ FAQ

**Q: Which window should I use?**  
A: Start with Hamming (best general purpose). Try Blackman for critical applications.

**Q: How do I change the cutoff frequency?**  
A: Edit `#define CUTOFF_FREQ 10.0f` in the .c file, then `make clean && make all`

**Q: Can I run all 5 programs on same input file?**  
A: Yes! Each creates a different output file: `filtered_<window>_filename.txt`

**Q: Will this break my existing setup?**  
A: No! Original files unchanged. New programs are independent.

**Q: How do I go back to original?**  
A: Just use `signal_analyzer_fixed` or the backup

---

## 🎯 Common Commands

```bash
# Compile everything
make all

# Compile one specific window
make hamming

# Remove all compiled executables
make clean

# Show help
make help

# Run with hamming window
./signal_analyzer_hamming adc_data/sample.txt

# Process entire directory with hamming
for file in adc_data/*.txt; do
  ./signal_analyzer_hamming "$file"
done

# View all results
ls filtered_hamming_*.txt

# Cleanup
make clean
```

---

## ✨ You're Ready!

Everything is compiled and waiting.  
Just pick your window and run the program.  
Enjoy exploring different filtering characteristics! 🎵

---

**Questions?** See `WINDOWING_IMPLEMENTATION_GUIDE.md` for detailed documentation.

---

Generated: 2026-05-18
