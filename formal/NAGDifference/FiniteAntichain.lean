namespace NAGDifference

/-- Placeholder predicate for antichain-style finite checks. -/
def HitsAtMostOnce {α : Type} (p : List α) (A : α → Prop) : Prop :=
  (p.filter A).length ≤ 1

end NAGDifference
