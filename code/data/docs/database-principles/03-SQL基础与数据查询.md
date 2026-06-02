# SQL 基础与数据查询

## 1. SQL 概述
SQL 是结构化查询语言，用于定义、操纵、控制关系数据库中的数据。

SQL 通常包含：
- 数据定义语言 DDL
- 数据操纵语言 DML
- 数据控制语言 DCL
- 事务控制语句

## 2. 常见数据类型
不同数据库系统语法略有差异，但常见类型包括：
- 整数：INT
- 浮点数：FLOAT、DOUBLE、DECIMAL
- 字符串：CHAR、VARCHAR、TEXT
- 日期时间：DATE、TIME、DATETIME、TIMESTAMP
- 布尔：BOOLEAN

## 3. 创建表
示例：

```sql
CREATE TABLE Student (
  Sno VARCHAR(20) PRIMARY KEY,
  Sname VARCHAR(50) NOT NULL,
  Major VARCHAR(50),
  Age INT
);
```

## 4. 插入数据
```sql
INSERT INTO Student (Sno, Sname, Major, Age)
VALUES ('2023001', '张三', '计算机科学', 20);
```

## 5. 修改与删除数据
### 更新
```sql
UPDATE Student
SET Age = 21
WHERE Sno = '2023001';
```

### 删除
```sql
DELETE FROM Student
WHERE Sno = '2023001';
```

## 6. 基本查询
### 查询全部列
```sql
SELECT * FROM Student;
```

### 查询指定列
```sql
SELECT Sno, Sname FROM Student;
```

### 条件查询
```sql
SELECT * FROM Student
WHERE Age > 20;
```

## 7. 排序与去重
### 排序
```sql
SELECT * FROM Student
ORDER BY Age DESC;
```

### 去重
```sql
SELECT DISTINCT Major FROM Student;
```

## 8. 聚合函数
常见聚合函数：
- COUNT
- SUM
- AVG
- MAX
- MIN

示例：

```sql
SELECT AVG(Age) AS avg_age
FROM Student;
```

## 9. 分组查询
```sql
SELECT Major, COUNT(*) AS total
FROM Student
GROUP BY Major;
```

配合 `HAVING` 可对分组结果继续筛选：

```sql
SELECT Major, COUNT(*) AS total
FROM Student
GROUP BY Major
HAVING COUNT(*) > 10;
```

## 10. 多表连接查询
```sql
SELECT s.Sname, c.Cname, sc.Grade
FROM Student s
JOIN SC sc ON s.Sno = sc.Sno
JOIN Course c ON sc.Cno = c.Cno;
```

## 11. 子查询
```sql
SELECT Sname
FROM Student
WHERE Sno IN (
  SELECT Sno
  FROM SC
  WHERE Grade > 90
);
```

## 12. 学习重点
- `WHERE`、`GROUP BY`、`HAVING` 区别
- 连接查询和子查询思路
- 聚合函数与分组统计
