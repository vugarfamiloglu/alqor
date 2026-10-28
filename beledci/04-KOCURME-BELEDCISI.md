# Alqor Bələdçisi — 5. Köçürmə Bələdçisi

> Artıq Python, JavaScript, C#, PHP və ya Java bilirsinizsə, bu cədvəllər
> sizi 30 dəqiqəyə Alqor-a keçirəcək.

---

## 5.1 Əsas konstruksiyalar — müqayisə cədvəli

| Əməliyyat | Python | JavaScript | C# | **Alqor** |
|---|---|---|---|---|
| Ekrana yaz | `print(x)` | `console.log(x)` | `Console.WriteLine(x)` | `yaz(x)` |
| Dəyişən | `x = 5` | `let x = 5` | `int x = 5` | `dəyişən x = 5` |
| Sabit | `X = 5` | `const x = 5` | `const int X = 5` | `sabit X = 5` |
| Şərt | `if x:` | `if (x) {` | `if (x) {` | `əgər x onda` |
| Əks hal | `else:` | `} else {` | `} else {` | `yoxsa` |
| Əks şərt | `elif x:` | `} else if (x) {` | `else if (x) {` | `yoxsa əgər x onda` |
| Blok sonu | girinti | `}` | `}` | `son` |
| Dövr (say) | `for i in range(5):` | `for (let i=0;i<5;i++)` | `for (int i=0;i<5;i++)` | `hər i üçün 0..<5 içində` |
| Dövr (siyahı) | `for x in lst:` | `for (const x of a)` | `foreach (var x in a)` | `hər x üçün s içində` |
| Şərtli dövr | `while x:` | `while (x) {` | `while (x) {` | `nə qədər ki x` |
| Funksiya | `def f(a):` | `function f(a) {` | `int F(int a) {` | `funksiya f(a)` |
| Qaytar | `return x` | `return x` | `return x` | `qaytar x` |
| Sinif | `class A:` | `class A {` | `class A {` | `sinif A` |
| Bu obyekt | `self` | `this` | `this` | `özü` |
| Baza sinif | `super()` | `super()` | `base` | `üst` |
| Yeni obyekt | `A()` | `new A()` | `new A()` | `yeni A()` |
| Miras | `class B(A):` | `class B extends A` | `class B : A` | `sinif B miras A` |
| Doğru/yanlış | `True`/`False` | `true`/`false` | `true`/`false` | `doğru`/`yanlış` |
| Boş | `None` | `null` | `null` | `boş` |
| Və | `and` | `&&` | `&&` | `və` |
| Və ya | `or` | `\|\|` | `\|\|` | `və ya` |
| Deyil | `not` | `!` | `!` | `deyil` |
| Try | `try:` | `try {` | `try {` | `cəhd et` |
| Catch | `except E as e:` | `catch (e) {` | `catch (E e) {` | `tut (e: E)` |
| Finally | `finally:` | `finally {` | `finally {` | `nəhayət` |
| Throw | `raise E()` | `throw new E()` | `throw new E()` | `at E()` |
| Import | `import m` | `import m from 'm'` | `using M;` | `gətir m` |
| Siyahı | `[1,2,3]` | `[1,2,3]` | `new[]{1,2,3}` | `[1,2,3]` |
| Lüğət | `{"a":1}` | `{a:1}` | `new Dictionary` | `{"a":1}` |
| Uzunluq | `len(x)` | `x.length` | `x.Count` | `uzunluq(x)` |
| Lambda | `lambda x: x*2` | `x => x*2` | `x => x*2` | `(x) => x*2` |
| Async | `async def` | `async function` | `async Task` | `asinxron funksiya` |
| Await | `await x` | `await x` | `await x` | `gözlə x` |
| Format | `f"{x}"` | `` `${x}` `` | `$"{x}"` | `"{x}"` |
| Şərh | `#` | `//` | `//` | `//` |

---

## 5.2 Python-dan Alqor-a

### Nümunə 1 — sadə dövr
```python
# Python
for i in range(1, 6):
    print("Rəqəm:", i)
```
```alqor
// Alqor
hər i üçün 1..5 içində
    yaz("Rəqəm:", i)
son
```

### Nümunə 2 — funksiya və siyahı
```python
# Python
def topla(sayilar):
    return sum(sayilar)

kvadratlar = [x**2 for x in range(10) if x % 2 == 0]
print(topla(kvadratlar))
```
```alqor
// Alqor
funksiya topla(ədədlər: siyahı[tam]) -> tam
    qaytar ədədlər.cəm()
son

dəyişən kvadratlar = [x ** 2 üçün x içində 0..<10 əgər x % 2 == 0]
yaz(topla(kvadratlar))
```

### Nümunə 3 — sinif
```python
# Python
class Insan:
    def __init__(self, ad, yas):
        self.ad = ad
        self.yas = yas

    def tanit(self):
        print(f"Mən {self.ad}")
```
```alqor
// Alqor
sinif İnsan
    qurucu(açıq xassə ad: mətn, açıq xassə yaş: tam)

    metod təqdim()
        yaz("Mən {özü.ad}")
    son
son
```

### Əsas fərqlər
| Python | Alqor |
|---|---|
| Girinti bloku müəyyən edir | `son` bloku bitirir, girinti sərbəstdir |
| `self` açıq parametrdir | `özü` avtomatikdir |
| Tipsiz | Tədrici tiplər |
| `0`, `""`, `[]` yanlış sayılır | Yalnız `yanlış` yanlışdır |
| GIL — həqiqi paralellik yoxdur | `sap` ilə həqiqi paralellik |
| `__init__`, `__str__` | `qurucu`, `mətnƏt` |

---

## 5.3 JavaScript-dən Alqor-a

### Nümunə 1 — asinxron
```javascript
// JavaScript
async function getUser(id) {
    const res = await fetch(`/api/user/${id}`);
    if (!res.ok) throw new Error("Not found");
    return await res.json();
}
```
```alqor
// Alqor
asinxron funksiya istifadəçiAl(id: tam) -> İstifadəçi
    dəyişən c = gözlə http.al("/api/istifadəçi/{id}")
    əgər deyil c.uğurludur() onda
        at Xəta("Tapılmadı")
    son
    qaytar c.json()
son
```

### Nümunə 2 — massiv metodları
```javascript
// JavaScript
const result = users
    .filter(u => u.age > 18)
    .map(u => u.name)
    .sort();
```
```alqor
// Alqor
dəyişən nəticə = istifadəçilər
    .filtr((i) => i.yaş > 18)
    .çevir((i) => i.ad)
    .sıralanmış()
```

### Nümunə 3 — komponent
```javascript
// React
function Counter() {
    const [count, setCount] = useState(0);
    return <button onClick={() => setCount(count+1)}>{count}</button>;
}
```
```alqor
// Alqor
komponent Sayğac
    vəziyyət say: tam = 0

    göstər()
        qaytar <button klik={() => özü.say += 1}>{özü.say}</button>
    son
son
```

### Əsas fərqlər
| JavaScript | Alqor |
|---|---|
| `==` tip çevirir | `==` çevirmir, həmişə sərtdir |
| `undefined` və `null` | yalnız `boş` |
| Prototip mirası | klassik siniflər |
| `var` hoisting | hoisting yoxdur |
| Tək ip (event loop) | `sap` ilə həqiqi paralellik |
| `npm` + `node_modules` | `alqorpm` + `paketlər/` |
| `useState`, `useEffect` | `vəziyyət`, `quraşdırıldı()` |

---

## 5.4 C#-dan Alqor-a

### Nümunə 1 — while dövrü
```csharp
// C#
int i = 1;
while (i <= 5)
{
    Console.WriteLine("Say: " + i);
    i++;
}
```
```alqor
// Alqor
dəyişən i = 1
nə qədər ki i <= 5
    yaz("Say: {i}")
    i++
son
```

### Nümunə 2 — LINQ
```csharp
// C#
var result = users
    .Where(u => u.Age > 18)
    .Select(u => u.Name)
    .OrderBy(n => n)
    .ToList();
```
```alqor
// Alqor
dəyişən nəticə = istifadəçilər
    .filtr((i) => i.yaş > 18)
    .çevir((i) => i.ad)
    .sıralanmış()
```

### Nümunə 3 — xassələr
```csharp
// C#
public class Rectangle {
    public double Width { get; set; }
    public double Height { get; set; }
    public double Area => Width * Height;
}
```
```alqor
// Alqor
sinif Düzbucaqlı
    açıq xassə en: onluq
    açıq xassə hündürlük: onluq

    xassə sahə: onluq
        oxu qaytar özü.en * özü.hündürlük son
    son
son
```

### Əsas fərqlər
| C# | Alqor |
|---|---|
| Nöqtəli vergül məcburi | lazım deyil |
| Fiqurlu mötərizə blokları | `son` |
| Metod yükləmə (overload) | yoxdur — standart dəyər və birləşmə tipi |
| `IEnumerable<T>` | `siyahı[T]`, generator |
| `async Task<T>` | `asinxron funksiya ... -> T` |
| NuGet | `alqorpm` |
| `.NET icra mühiti` lazımdır | tək statik binar |

---

## 5.5 PHP-dən Alqor-a

```php
// PHP
<?php
for ($i = 1; $i <= 5; $i++) {
    echo "Rəqəm: " . $i . "<br>";
}
?>
```
```alqor
// Alqor (veb)
hər i üçün 1..5 içində
    yaz("Rəqəm: {i}")
son
```

### Veb server müqayisəsi
```php
// PHP — Apache/nginx + PHP-FPM lazımdır
<?php
$users = $pdo->query("SELECT * FROM users")->fetchAll();
foreach ($users as $u) {
    echo "<li>" . htmlspecialchars($u['name']) . "</li>";
}
```
```alqor
// Alqor — heç nə lazım deyil, tək binar
dəyişən istifadəçilər = gözlə b.sorğu("SELECT * FROM istifadəçilər")
// şablonda:
// {% hər i üçün istifadəçilər içində %}<li>{{ i.ad }}</li>{% son %}
// htmlspecialchars avtomatikdir
```

| PHP | Alqor |
|---|---|
| `$` prefiksi | yoxdur |
| `echo` | `yaz` |
| `.` birləşdirmə | `+` və ya `"{x}"` |
| `->` | `.` |
| `::` | `.` |
| Veb server lazımdır | daxili server |
| `composer` | `alqorpm` |
| `htmlspecialchars` əl ilə | avtomatik |

---

## 5.6 Tez-tez edilən səhvlər

### ❌ `son` unudulur
```alqor
əgər x > 5 onda
    yaz("böyük")
// ✖ ALQ-P002: `son` gözlənilirdi
```

### ❌ `onda` unudulur
```alqor
əgər x > 5
    yaz("böyük")
son
// ✖ ALQ-P004: `onda` gözlənilirdi
```

### ❌ Şərtdə ədəd
```alqor
əgər 1 onda ... son              // ✖ ALQ-T007
əgər siyahı onda ... son         // ✖ ALQ-T007

// Düzgün:
əgər x != 0 onda ... son
əgər deyil boşdur(siyahı) onda ... son
```

### ❌ Mətn + ədəd
```alqor
yaz("Yaş: " + 24)                // ✖ ALQ-T008

// Düzgün:
yaz("Yaş: {24}")
yaz("Yaş: " + mətnƏt(24))
```

### ❌ `özü` unudulur
```alqor
sinif A
    xassə ad: mətn
    metod f()
        yaz(ad)                  // ✖ ALQ-T050
        yaz(özü.ad)              // ✓
    son
son
```

### ❌ `əvəz et` unudulur
```alqor
sinif B miras A
    metod f() ... son            // ✖ ALQ-T051
    əvəz et metod f() ... son    // ✓
son
```

### ❌ Onluq ayırıcı kimi vergül
```alqor
yaz(3,14)                        // iki arqument: 3 və 14
yaz(3.14)                        // ✓ bir ədəd
```

### ❌ `i++` ifadə daxilində
```alqor
dəyişən b = i++                  // ✖ ALQ-P015
i++                              // ✓ müstəqil ifadə kimi
dəyişən b = i; i += 1            // ✓
```

### ❌ ASCII və Azərbaycan hərfləri qarışdırılır
```alqor
dəyişən yaş = 24
yaz(yas)                         // ✖ ALQ-T022: `yas` təyin edilməyib
```
> Dəyişən adlarında ASCII çevrilməsi **yoxdur** — yalnız açar sözlərdə var.

---

## 5.7 Köçürmə alətləri

```bash
# Python kodundan ilkin Alqor skeleti yaradır
alqor köçür --mənbə python əsas.py

# JavaScript-dən
alqor köçür --mənbə js app.js
```

> Bu alət **avtomatik tərcümə deyil** — 70-80% hazır kod verir, qalanını
> əl ilə yoxlamaq lazımdır. Xüsusilə tipləri və `boş` davranışını.

---

**Növbəti:** [6. Xəta Lüğəti](05-XETA-LUGETI.md)
