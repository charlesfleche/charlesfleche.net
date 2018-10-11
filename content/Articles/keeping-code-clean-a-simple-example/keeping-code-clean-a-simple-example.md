Title: Keeping code clean: a simple example
Slug: keeping-code-clean-a-simple-example
Date: 2018-10-10 09:00
Tags: refactoring, js, vue
Lang: en
Abstract: A baby-step by baby-step example on how to keep code clean
Tweet: Keeping #code clean: a simple example

During a code review a member of team presented a piece of code that presented a good opportunity to showcase how simple code cleaning technique would improve the code quality from *working* to *maintainable*. First, here is the code **after** cleaning:

``` js
export default {
  /* Other members are declared
  ...
  */
  emitChange (ev) {
    const value = this.toEmitValue(ev.target.value)
    if (isWeekend(value)) {
      alert(`Holidays isn't allowed to select!`)
    } else {
      this.$emit('input', value)
    }
  }
}

function isWeekend (timestamp) {
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
        alert('Holidays isn\'t allowed to select!')
        return
        break
      default:
        this.$emit('input', date)
        break
    }
  }
}
```

It starts the same way:
1. `emitChange` receives an event. By its name `emit*`, it is supposed that it eventually emits a message
2. `this.isHoliday` is called. By its name `is*`, it is supposed to be a predicate (in a few words, a predicate is function that takes one and several values and returns a boolean). But `emitChange` does not return anything and more importantly does not call `this.$emit` at all. Something is weird here: we have to dig into the called functions code to understand what it going on here.
3. looking at `isHoliday`, we see that the action (`alert` or `$emit`) are actually called here within switch cases: `isHoliday` was not a predicate after all.
4. `preventHolidaySelect` looks like an action: the verb `prevent` let the reader thinks that this function may have a side effect. However, why would an action be used as a switch condition in this context ? Again, something is off weird, and we need to read `preventHolidaySelect` to understand what it does.
5. Turns out `preventHolidaySelect` is query function that returns the day of the week index (1 is Monday, 2 is Tuesday, etc) from a timestamp. It it not an action and has no side effects.

This code suffers from several defects, but the most important is that function names are confusing: a predicate is not predicate, an action is actually a query, an `emit*` does not emit anything.

Let's see how a few baby-steps can help the code to better convey its intent, making it more maintainable.
