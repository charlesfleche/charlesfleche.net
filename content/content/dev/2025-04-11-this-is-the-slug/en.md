Title: The title
Description: This is the description of the article

![The linked image alt text](test.webp "The linked image title")
![The linked movie alt text](test.mp4 "The linked movie title")

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
