Title: Keeping code clean: a simple example
Slug: keeping-code-clean-a-simple-example
Date: 2018-10-10 09:00
Tags: refactoring, js, vue
Lang: en
Abstract: A baby-step by baby-step example on how to keep code clean
Tweet: Keeping #code clean: a simple example

# Readable code…

During a code review a member of team presented a piece of code that presented a good opportunity to showcase how simple code cleaning technique would improve the code quality from *working* to *maintainable*. First, here is the code **after** cleaning:

``` js
export default {
  /* Other members are declared
  ...
  */
  emitChange (ev) {
    const value = this.toEmitValue(ev.target.value)
    if (isHoliday(value)) {
      alert(`Holidays isn't allowed to select!`)
    } else {
      this.$emit('input', value)
    }
  }
}

function isHoliday (timestamp) {
  const day = timestampToDayOfWeek(timestamp)
  return day !== 0 && day !== 6
}

function timestampToDayOfWeek (timestamp) {
  const date = new Date(timestamp)
  return date.getDay()
}
```

The intent here is pretty clear:

1. `emitChange` receives an event. By its name (`emit*`) it is supposed that it eventually emits a message
2. the value to be emitted is extracted from the event
3. depending if the value represents a weekend or not, an alert is displayed or the value emitted

All functions called by `emitChange` are all at the same level of abstraction: extract / query / action are directly called, but the implementation details lay in each function body, not in `emitChange` itself. A reader does not have to dig deeper into the called functions to understand what `emitChange` does.

# …has to start somewhere

Now let's take a look at the original code **before** cleaning:

``` js
export default {
  /* Other members are declared
  ...
  */
  preventHolidaySelect (timestamp) {
    const date = new Date(timestamp)
    return date.getDay()
  },
  emitChange (ev) {
    const value = this.toEmitValue(ev.target.value)
    this.isHoliday(value)
  },
  isHoliday (date) {
    switch(this.preventHolidaySelect(date)) {
      case 0: // Saturday
      case 6: // Sunday
        alert('Can not select a day off')
        return
        break
      default:
        this.$emit('input', date)
        break
    }
  }
}
```

It starts the same way, but quickly the code raises a few questions:

1. `emitChange` receives an event. By its name `emit*`, it is supposed that it eventually emits a message
2. `this.isHoliday` is called. By its name `is*`, it is supposed to be a predicate (in a few words, a [predicate](https://en.wikipedia.org/wiki/Predicate_(mathematical_logic)) is function that takes one and several values and returns a boolean). But `emitChange` does not return anything and more importantly does not call `this.$emit` at all. Something is weird here: we have to dig into the called functions code to understand what it going on here.
3. looking at `isHoliday`, we see that the action (`alert` or `$emit`) are actually called here within switch cases: `isHoliday` was not a predicate after all.
4. `preventHolidaySelect` looks like an action: the verb `prevent` let the reader thinks that this function may have a side effect. However, why would an action be used as a switch condition in this context ? Again, something is off weird, and we need to read `preventHolidaySelect` to understand what it does.
5. Turns out `preventHolidaySelect` is query function that returns the day of the week index (1 is Monday, 2 is Tuesday, etc) from a timestamp. It it not an action and has no side effects.

This code suffers from several defects, but the most important is that function names are confusing: a predicate is not predicate, an action is actually a query, an `emit*` does not emit anything.

# Cleaning code, little by little

Let's see how a few baby-steps can help the code to better convey its intent, making it more maintainable.

## Rename `preventHolidaySelect` to `timestampToDayOfWeek`

This conveys the real purpose of the function: converting a `timestamp` `To` a `DayOfWeek`.

``` diff
@@ -38,7 +38,7 @@ export default {
     }
   },
   methods: {
-    preventHolidaySelect(timestamp) {
+    timestampToDayOfWeek(timestamp) {
       const date = new Date(timestamp)
       return date.getDay()
     },
@@ -47,7 +47,7 @@ export default {
       this.isHoliday(value)
     },
     isHoliday(date) {
-      switch(this.preventHolidaySelect(date)) {
+      switch(this.timestampToDayOfWeek(date)) {
         case 0: // Saturday
         case 6: // Sunday
           alert('Can not select a day off')
```

## Extract `timestampToDayOfWeek` to its own function

The method `timestampToDayOfWeek` is a member of an object: it is called from `this`, and inside the function body `this` points to the object owning the function. However it not necessary as `timestampToDayOfWeek` only operates on its argument. As such it should not belong to the object and needs to be extracted to its own function. This will make it reusable in other parts of the code and more easily testable.

``` diff
@@ -38,16 +38,12 @@ export default {
   methods: {
-    timestampToDayOfWeek(timestamp) {
-      const date = new Date(timestamp)
-      return date.getDay()
-    },
     emitChange(ev) {
       const value = this.toEmitValue(ev.target.value)
       this.isHoliday(value)
     },
     isHoliday(date) {
-      switch(this.timestampToDayOfWeek(date)) {
+      switch(timestampToDayOfWeek(date)) {
         case 0: // Saturday
         case 6: // Sunday
           alert('Can not select a day off')
@@ -74,6 +70,11 @@ export default {
     }
   }
 }
+
+function timestampToDayOfWeek(timestamp) {
+  const date = new Date(timestamp)
+  return date.getDay()
+}
```

## Extract `isHoliday` to its own predicate

The function `isHoliday` has two intents:

1. it implements the predicate logic that checks if a day is an holiday
2. it acts upon the result of the predicate by calling either `$emit` or `alert`

Two intents in a function makes it harder to test. It is also confusing to the reader: by its name starting with `is*`, `isHoliday` is supposed to be a predicate that just returns a boolean. However it has side-effect: `$emit` or `alert` can change the state of the system.

The next change actually makes `isHoliday` a predicate and move the resulting actions `$emit` or `alert` in the calling code `emitChange`.

``` diff
@@ -40,18 +40,19 @@ export default {
   methods: {
     emitChange(ev) {
       const value = this.toEmitValue(ev.target.value)
-      this.isHoliday(value)
+      if (this.isHoliday(value)) {
+        alert('Can not select a day off')
+      } else {
+        this.$emit('input', value)
+      }
     },
     isHoliday(date) {
       switch(timestampToDayOfWeek(date)) {
         case 0: // Saturday
         case 6: // Sunday
-          alert('Can not select a day off')
-          return
-          break
+          return true
         default:
-          this.$emit('input', date)
-          break
+          return false
       }
     },
```

## Clarify the expected type of the `isHoliday` argument

Javascript being a [dynamically typed language](https://stackoverflow.com/questions/1517582/what-is-the-difference-between-statically-typed-and-dynamically-typed-languages), function arguments can be of any types. Naming is crucial. Here `isHoliday` expects a timestamp. However its argument is named `date`, which could very be a [`Date`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date) instance. Renaming the argument clarifies the expected type.

``` diff
@@ -46,8 +46,8 @@ export default {
         this.$emit('input', value)
       }
     },
-    isHoliday(date) {
-      switch(timestampToDayOfWeek(date)) {
+    isHoliday(timestamp) {
+      switch(timestampToDayOfWeek(timestamp)) {
         case 0: // Saturday
         case 6: // Sunday
           return true
```

## Directly returns the predicate computation

Functions that compute a boolean as an `if` condition just to return it in the `then` and `else` block are easy wins when cleaning code. Compare `indirectPredicate` and `directPredicate`.

``` js
function indirectPredicate (arg) {
  if (predicate1(arg) &&
      predicate2(arg) &&
      predicate3(arg)) {
    return true
  } else {
    return false
  }
}

function directPredicate (arg) {
  return predicate1(arg) && predicate2(arg) && predicate3(arg)
}
```

Both functions are equivalent, but in my opinion `directPredicate` is much easier to read. The current version of `isHoliday` implements a variant of this anti-pattern with a `switch`. This is easily cleaned up:

``` diff
@@ -47,12 +47,8 @@ export default {
     isHoliday(timestamp) {
-      switch(timestampToDayOfWeek(timestamp)) {
-        case 0: // Saturday
-        case 6: // Sunday
-          return true
-        default:
-          return false
+      const day = timestampToDayOfWeek(timestamp)
+      return day !== 0 && day !== 6
       }
     },
```

## Extract `timestampToDayOfWeek` to its own function

The same way `timestampToDayOfWeek` has been moved outside of the object, now that `isHoliday` does not call `this.$emit` anymore, it can be extracted to its own function for better reusability and testability.

``` diff
methods: {
  emitChange(ev) {
    const value = this.toEmitValue(ev.target.value)
-      if (this.isHoliday(value)) {
+      if (isHoliday(value)) {
      alert('Can not select a day off')
    } else {
      this.$emit('input', value)
    }
  },
-    isHoliday(timestamp) {
-      const day = timestampToDayOfWeek(timestamp)
-      return day !== 0 && day !== 6
-      }
-    },
  toEmitValue(value) {
    return inputStringToMilliseconds (value)
  },
@@ -72,6 +67,11 @@ function timestampToDayOfWeek(timestamp) {
const date = new Date(timestamp)
return date.getDay()
}
+
+function isHoliday(timestamp) {
+  const day = timestampToDayOfWeek(timestamp)
+  return day !== 0 && day !== 6
+}
```

# Conclusion

Let's take another look at the code before and after refactoring. In term logic, both versions are absolutely equivalent. But cleaning up brought up **explicit code** that **does not hide its intent** and is **easily testable**. All those changes may seem pedantic, but at the scale of a large application they really make a difference in maintainability.

Those examples have been extracted from a project where automated testing could be improved by an order of magnitude. But the first step to **testing** is to **write testable code**: that starts with clean code.
