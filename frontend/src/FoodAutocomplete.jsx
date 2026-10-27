import React, {useId, useState} from 'react';

// 등록된 음식명만 기존 class_id로 연결한다. 미완성 입력은 저장하지 않는다.
export default function FoodAutocomplete({foods, value, onChange, autoFocus}) {
  const listId = useId();
  const [query, setQuery] = useState(() => foods.find(food => food.class_id === value)?.food_name || '');
  return <>
    <input type="text" list={listId} value={query} autoFocus={autoFocus}
      placeholder="음식명을 입력해 검색하세요" autoComplete="off"
      onChange={event => {
        const text = event.target.value;
        setQuery(text);
        const food = foods.find(item => item.food_name === text.trim());
        onChange(food?.class_id ?? null);
      }}/>
    <datalist id={listId}>{foods.map(food => <option key={food.class_id} value={food.food_name}/>)}</datalist>
    {query && value == null && <small className="muted">검색 후보에서 등록된 음식을 선택해 주세요.</small>}
  </>;
}
