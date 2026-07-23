a = [[1, 2], [3, 4]]
b = a[:]

b[0].append(5)

print(a)
print(b)
print(a is b)
print(a[0] is b[0])